from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional, Tuple, Dict, Any

from sqlalchemy import select, cast, Numeric, desc, asc
from sqlalchemy.orm import Session

from app.models.compensatory_event import CompensatoryEvent
from app.models.default_event import DefaultEvent
from app.models.settlement_result import SettlementResult
from app.models.quote_bid import QuoteBid
from app.models.round import Round


class CompensatoryService:
    def _get_existing(self, db: Session, workflow: str, project_id: uuid.UUID, t: int) -> Optional[CompensatoryEvent]:
        return db.execute(
            select(CompensatoryEvent).where(
                CompensatoryEvent.workflow == workflow,
                CompensatoryEvent.project_id == project_id,
                CompensatoryEvent.t == t,
            )
        ).scalar_one_or_none()

    def _get_default(self, db: Session, workflow: str, project_id: uuid.UUID, t: int) -> Optional[DefaultEvent]:
        return db.execute(
            select(DefaultEvent).where(
                DefaultEvent.workflow == workflow,
                DefaultEvent.project_id == project_id,
                DefaultEvent.t == t,
            )
        ).scalar_one_or_none()

    def _get_settlement(self, db: Session, workflow: str, project_id: uuid.UUID, t: int) -> Optional[SettlementResult]:
        return db.execute(
            select(SettlementResult).where(
                SettlementResult.workflow == workflow,
                SettlementResult.project_id == project_id,
                SettlementResult.t == t,
            )
        ).scalar_one_or_none()

    def _get_round(self, db: Session, workflow: str, project_id: uuid.UUID, t: int) -> Optional[Round]:
        return db.execute(
            select(Round).where(Round.workflow == workflow, Round.project_id == project_id, Round.t == t)
        ).scalar_one_or_none()

    def _eligible_quotes(self, db: Session, workflow: str, project_id: uuid.UUID, t: int, exclude_bid_id: uuid.UUID):
        qbundle_num = cast(QuoteBid.payload_json["qbundle_inr"].astext, Numeric(20, 2))
        # Eligible: locked, has qbundle, not the original winner
        return db.execute(
            select(QuoteBid.id, qbundle_num)
            .where(
                QuoteBid.workflow == workflow,
                QuoteBid.project_id == project_id,
                QuoteBid.t == t,
                QuoteBid.state == "locked",
                QuoteBid.payload_json.has_key("qbundle_inr"),
                QuoteBid.id != exclude_bid_id,
            )
            .order_by(desc(qbundle_num), asc(QuoteBid.id))
        ).all()

    def compute_and_store_if_needed(self, db: Session, *, workflow: str, project_id: uuid.UUID, t: int) -> CompensatoryEvent:
        existing = self._get_existing(db, workflow, project_id, t)
        if existing:
            return existing

        default_ev = self._get_default(db, workflow, project_id, t)
        if not default_ev:
            raise ValueError("No default recorded; compensatory obligation transfer not applicable.")

        rnd = self._get_round(db, workflow, project_id, t)
        if not rnd or not rnd.is_locked:
            raise ValueError("Round must be locked for compensatory event computation.")

        settlement = self._get_settlement(db, workflow, project_id, t)
        if not settlement:
            raise ValueError("SettlementResult not found.")

        if settlement.winner_quote_bid_id is None or settlement.second_price_quote_bid_id is None or settlement.second_price_inr is None:
            raise ValueError("Settlement missing original winner/second-price; cannot enforce bsecond constraint.")

        original_winner = settlement.winner_quote_bid_id
        original_second = settlement.second_price_quote_bid_id
        original_bsecond = Decimal(str(settlement.second_price_inr))

        notes: Dict[str, Any] = {
            "trigger": "default_event",
            "constraint": "bsecond,new ≤ bsecond",
            "enforcement": "if bsecond,new > bsecond then set to bsecond",
            "original_sources": {
                "winner_quote_bid_id": str(original_winner),
                "second_price_quote_bid_id": str(original_second),
                "bsecond_source": "SettlementResult.second_price_inr",
            },
        }

        eligible = self._eligible_quotes(db, workflow, project_id, t, exclude_bid_id=original_winner)

        if len(eligible) == 0:
            row = CompensatoryEvent(
                workflow=workflow,
                project_id=project_id,
                round_id=settlement.round_id,
                t=t,
                settlement_result_id=settlement.id,
                default_event_id=default_ev.id,
                status="no_reallocation_no_eligible_bidders",
                original_winner_quote_bid_id=original_winner,
                original_second_quote_bid_id=original_second,
                original_bsecond_inr=original_bsecond,
                enforcement_action="none",
                notes_json={**notes, "result": "no_eligible_quotes"},
            )
            db.add(row); db.commit(); db.refresh(row)
            return row

        # New winner = highest among eligible (already ordered desc)
        new_winner_id, new_winner_val = eligible[0][0], Decimal(str(eligible[0][1]))

        # New second = next best among eligible excluding new winner
        if len(eligible) >= 2:
            new_second_id, new_second_val = eligible[1][0], Decimal(str(eligible[1][1]))
        else:
            new_second_id, new_second_val = None, None

        enforcement_action = "none"
        bsecond_new_raw = new_second_val
        bsecond_new_enforced = new_second_val

        if bsecond_new_raw is None:
            # cannot form second price, keep event computed but incomplete
            status = "insufficient_bidders_for_new_second_price"
            notes["result"] = "only_one_eligible_quote_remaining"
        else:
            # Enforce constraint exactly
            if bsecond_new_raw > original_bsecond:
                bsecond_new_enforced = original_bsecond
                enforcement_action = "clamped_to_original_bsecond"
                notes["clamp"] = {
                    "bsecond_new_raw_inr": str(bsecond_new_raw),
                    "bsecond_original_inr": str(original_bsecond),
                    "bsecond_new_enforced_inr": str(bsecond_new_enforced),
                }
            status = "computed"

        row = CompensatoryEvent(
            workflow=workflow,
            project_id=project_id,
            round_id=settlement.round_id,
            t=t,
            settlement_result_id=settlement.id,
            default_event_id=default_ev.id,
            status=status,
            original_winner_quote_bid_id=original_winner,
            original_second_quote_bid_id=original_second,
            original_bsecond_inr=original_bsecond,
            new_winner_quote_bid_id=new_winner_id,
            new_second_quote_bid_id=new_second_id,
            bsecond_new_raw_inr=bsecond_new_raw,
            bsecond_new_enforced_inr=bsecond_new_enforced,
            enforcement_action=enforcement_action,
            notes_json=notes,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row