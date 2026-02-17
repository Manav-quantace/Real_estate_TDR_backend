# app/services/settlement_service.py
from __future__ import annotations

import uuid
from typing import Optional, Tuple, Dict, Any
from decimal import Decimal

from sqlalchemy import select, cast, Numeric, desc, asc
from sqlalchemy.orm import Session

from app.models.round import Round
from app.models.matching_result import MatchingResult
from app.models.quote_bid import QuoteBid
from app.models.ask_bid import AskBid
from app.models.settlement_result import SettlementResult
from app.models.tokenized_contract import TokenizedContractRecord  # ✅ NEW

from app.services.matching_service import MatchingService
from app.services.ledger_service import LedgerService


class SettlementService:
    """
    Computes economic settlement and records final truth
    to the immutable contract ledger.
    """

    # ─────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────

    def _get_round(
        self,
        db: Session,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
    ) -> Optional[Round]:
        return db.execute(
            select(Round).where(
                Round.workflow == workflow,
                Round.project_id == project_id,
                Round.t == t,
            )
        ).scalar_one_or_none()

    def _get_existing(
        self,
        db: Session,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
    ) -> Optional[SettlementResult]:
        return db.execute(
            select(SettlementResult).where(
                SettlementResult.workflow == workflow,
                SettlementResult.project_id == project_id,
                SettlementResult.t == t,
            )
        ).scalar_one_or_none()

    def _get_matching(
        self,
        db: Session,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
    ) -> MatchingResult:
        return MatchingService().compute_and_store_if_needed(
            db,
            workflow=workflow,
            project_id=project_id,
            t=t,
        )

    def _second_highest_quote(
        self,
        db: Session,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
        winner_quote_id: uuid.UUID,
    ) -> Optional[Tuple[uuid.UUID, Decimal]]:
        qbundle_num = cast(
            QuoteBid.payload_json["qbundle_inr"].astext,
            Numeric(20, 2),
        )

        row = db.execute(
            select(QuoteBid.id, qbundle_num)
            .where(
                QuoteBid.workflow == workflow,
                QuoteBid.project_id == project_id,
                QuoteBid.t == t,
                QuoteBid.state == "locked",
                QuoteBid.payload_json.has_key("qbundle_inr"),
                QuoteBid.id != winner_quote_id,
            )
            .order_by(desc(qbundle_num), asc(QuoteBid.id))
            .limit(1)
        ).one_or_none()

        if not row:
            return None

        return row[0], row[1]

    # ─────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────

    def compute_and_store_if_needed(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
    ) -> SettlementResult:
        """
        Computes settlement once per round and writes final economic truth
        to the immutable contract ledger.
        """

        # Idempotency
        existing = self._get_existing(db, workflow, project_id, t)
        if existing:
            return existing

        rnd = self._get_round(db, workflow, project_id, t)
        if not rnd:
            raise ValueError("Round not found.")
        if not rnd.is_locked:
            raise ValueError("Settlement can be computed only after round lock.")

        match = self._get_matching(db, workflow, project_id, t)

        receipt: Dict[str, Any] = {
            "vickrey_rule": "winner pays second-highest applicable price",
            "matching_result_id": str(match.id),
        }

        matched = bool(
            match.matched == "true"
            if isinstance(match.matched, str)
            else match.matched
        )

        # ─────────────────────────────
        # NO MATCH
        # ─────────────────────────────
        if not matched or not match.selected_quote_bid_id or not match.selected_ask_bid_id:
            row = SettlementResult(
                workflow=workflow,
                project_id=project_id,
                round_id=rnd.id,
                t=t,
                matching_result_id=match.id,
                status="computed",
                settled=False,
                receipt_json={**receipt, "status": "no_settlement"},
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return row

        # ─────────────────────────────
        # MATCHED
        # ─────────────────────────────

        winner_quote_id = match.selected_quote_bid_id
        winning_ask_id = match.selected_ask_bid_id

        winner_quote = db.execute(
            select(QuoteBid).where(QuoteBid.id == winner_quote_id)
        ).scalar_one()

        winning_ask = db.execute(
            select(AskBid).where(AskBid.id == winning_ask_id)
        ).scalar_one()

        second = self._second_highest_quote(
            db, workflow, project_id, t, winner_quote_id
        )

        if not second:
            row = SettlementResult(
                workflow=workflow,
                project_id=project_id,
                round_id=rnd.id,
                t=t,
                matching_result_id=match.id,
                status="computed",
                settled=False,
                receipt_json={**receipt, "status": "no_second_price"},
            )
            db.add(row)
            db.commit()
            db.refresh(row)
            return row

        second_id, second_price = second
        second_quote = db.execute(
            select(QuoteBid).where(QuoteBid.id == second_id)
        ).scalar_one()

        # ─────────────────────────────
        # CREATE SETTLEMENT RESULT
        # ─────────────────────────────
        settlement = SettlementResult(
            workflow=workflow,
            project_id=project_id,
            round_id=rnd.id,
            t=t,
            matching_result_id=match.id,
            status="computed",
            settled=True,
            receipt_json={**receipt, "status": "settled"},
        )

        db.add(settlement)
        db.commit()
        db.refresh(settlement)

        # ─────────────────────────────
        # ✅ CREATE CONTRACT (CRITICAL FIX)
        # ─────────────────────────────
        contract = TokenizedContractRecord(
            id=uuid.uuid4(),
            workflow=workflow,
            project_id=project_id,
            t=t,
            settlement_result_id=settlement.id,
            buyer_participant_id=winner_quote.participant_id,
            developer_participant_id=winning_ask.participant_id,
            settlement_price_inr=second_price,
        )

        db.add(contract)
        db.commit()
        db.refresh(contract)

        # ─────────────────────────────
        # 🔐 LEDGER WRITE (NOW VALID)
        # ─────────────────────────────
        LedgerService().append_entry(
            db,
            workflow=workflow,
            project_id=project_id,
            contract_id=contract.id,  # ✅ CORRECT
            entry_type="SETTLEMENT_EXECUTED",
            payload={
                "round": t,
                "contract_id": str(contract.id),
                "settlement_result_id": str(settlement.id),
                "winner_quote_bid_id": str(winner_quote_id),
                "winning_ask_bid_id": str(winning_ask_id),
                "second_price_quote_bid_id": str(second_id),
                "second_price_inr": str(second_price),
                "winner_quote_signature_hash": winner_quote.signature_hash,
                "winning_ask_signature_hash": winning_ask.signature_hash,
                "second_quote_signature_hash": second_quote.signature_hash,
            },
        )

        return settlement
