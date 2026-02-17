# app/services/matching_service.py
from __future__ import annotations

import uuid
from typing import Optional, Tuple
from decimal import Decimal

from sqlalchemy import select, cast, Numeric, asc, desc
from sqlalchemy.orm import Session

from app.models.round import Round
from app.models.ask_bid import AskBid
from app.models.quote_bid import QuoteBid
from app.models.matching_result import MatchingResult
from app.models.subsidized_economic_model import SubsidizedEconomicModel
from app.models.government_charge import GovernmentCharge
from app.services.clearland_phase_service import ClearlandPhaseService
from app.core.clearland_phases import ClearlandPhaseType


class MatchingService:
    def _get_round(
        self, db: Session, workflow: str, project_id: uuid.UUID, t: int
    ) -> Optional[Round]:
        return db.execute(
            select(Round).where(
                Round.workflow == workflow,
                Round.project_id == project_id,
                Round.t == t,
            )
        ).scalar_one_or_none()

    def _get_existing(
        self, db: Session, workflow: str, project_id: uuid.UUID, t: int
    ) -> Optional[MatchingResult]:
        return db.execute(
            select(MatchingResult).where(
                MatchingResult.workflow == workflow,
                MatchingResult.project_id == project_id,
                MatchingResult.t == t,
            )
        ).scalar_one_or_none()

    # -------------------------
    # SALEABLE / SLUM HELPERS
    # -------------------------
    def _select_min_ask(
        self, db: Session, workflow: str, project_id: uuid.UUID, t: int
    ) -> Optional[Tuple[uuid.UUID, Decimal]]:
        row = db.execute(
            select(AskBid.id, AskBid.total_ask_inr)
            .where(
                AskBid.workflow == workflow,
                AskBid.project_id == project_id,
                AskBid.t == t,
                AskBid.state == "locked",
                AskBid.total_ask_inr.is_not(None),
            )
            .order_by(asc(AskBid.total_ask_inr), asc(AskBid.id))
            .limit(1)
        ).one_or_none()
        if not row:
            return None
        return row[0], row[1]

    def _select_max_quote(
        self, db: Session, workflow: str, project_id: uuid.UUID, t: int
    ) -> Optional[Tuple[uuid.UUID, Decimal]]:
        qbundle_num = cast(QuoteBid.payload_json["qbundle_inr"].astext, Numeric(20, 2))
        row = db.execute(
            select(QuoteBid.id, qbundle_num)
            .where(
                QuoteBid.workflow == workflow,
                QuoteBid.project_id == project_id,
                QuoteBid.t == t,
                QuoteBid.state == "locked",
                QuoteBid.payload_json.has_key("qbundle_inr"),
            )
            .order_by(desc(qbundle_num), asc(QuoteBid.id))
            .limit(1)
        ).one_or_none()
        if not row:
            return None
        return row[0], row[1]

    # -------------------------
    # SUBSIDIZED HELPERS
    # -------------------------
    def _get_published_economic_model(
        self, db: Session, project_id: uuid.UUID
    ) -> SubsidizedEconomicModel:
        row = (
            db.query(SubsidizedEconomicModel)
            .filter_by(project_id=project_id, is_published_version=True)
            .first()
        )
        if not row:
            raise ValueError("Published subsidized economic model not found.")
        return row

    def _resolve_gcu(
        self, db: Session, *, project_id: uuid.UUID, round_id: uuid.UUID
    ) -> Decimal:
        """
        Resolve GCU to use for this round:
        1) Prefer round-level GovernmentCharge (charge_type == "GCU")
        2) Fallback to published economic model.gcu
        """
        row = db.execute(
            select(GovernmentCharge.value_inr).where(
                GovernmentCharge.round_id == round_id,
                GovernmentCharge.charge_type == "GCU",
            )
        ).scalar_one_or_none()

        if row is not None:
            return Decimal(str(row))
        model = self._get_published_economic_model(db, project_id)
        return Decimal(str(model.gcu or 0))

    def _select_min_effective_cost_ask(
        self,
        db: Session,
        *,
        project_id: uuid.UUID,
        t: int,
        gcu: Decimal,
    ) -> Optional[Tuple[uuid.UUID, Decimal]]:
        effective_cost = AskBid.total_ask_inr + gcu

        row = db.execute(
            select(AskBid.id, effective_cost)
            .where(
                AskBid.workflow == "subsidized",
                AskBid.project_id == project_id,
                AskBid.t == t,
                AskBid.state == "locked",
                AskBid.total_ask_inr.is_not(None),
            )
            .order_by(asc(effective_cost), asc(AskBid.id))
            .limit(1)
        ).one_or_none()

        if not row:
            return None
        return row[0], row[1]

    # -------------------------
    # MAIN ENTRY
    # -------------------------
    def compute_and_store_if_needed(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
    ) -> MatchingResult:
        existing = self._get_existing(db, workflow, project_id, t)
        if existing:
            return existing

        rnd = self._get_round(db, workflow, project_id, t)
        if not rnd:
            raise ValueError("Round not found.")
        if not rnd.is_locked:
            raise ValueError("Matching can be triggered only after round lock.")

        matched = False
        selected_ask_id = None
        selected_quote_id = None
        min_ask_val = None
        max_quote_val = None

        # -------------------------
        # SUBSIDIZED LOGIC (BOOK)
        # -------------------------
        if workflow == "subsidized":
            gcu = self._resolve_gcu(db, project_id=project_id, round_id=rnd.id)

            min_eff = self._select_min_effective_cost_ask(
                db, project_id=project_id, t=t, gcu=gcu
            )
            max_quote = self._select_max_quote(db, workflow, project_id=project_id, t=t)

            notes = {
                "rule": "min(Ask.total_ask_inr + GCU) ↔ max(Quote.qbundle_inr)",
                "gcu": str(gcu),
                "objective": "minimize(DCU + GCU)",
            }

            if not min_eff:
                notes["reason"] = "no_locked_asks"
            else:
                selected_ask_id, min_ask_val = min_eff

            if not max_quote:
                notes["reason_quote"] = "no_locked_quotes"
            else:
                selected_quote_id, max_quote_val = max_quote

            if min_ask_val is not None and max_quote_val is not None:
                matched = Decimal(str(max_quote_val)) >= Decimal(str(min_ask_val))
                notes["condition"] = "max_quote_inr >= (ask + gcu)"

        
        # 🔐 CLEARLAND PHASE GUARD (NO-OP FOR OTHERS)
        if workflow == "clearland":
            phase = ClearlandPhaseService().get_current_phase(
                db, project_id=project_id
            )
            if not phase:
                raise ValueError("Clearland phase not initialized.")

            if phase.phase not in {
                ClearlandPhaseType.LOCKED.value,
                ClearlandPhaseType.COMPLETED.value,
            }:
                raise ValueError(
                    f"Matching not allowed during clearland phase {phase.phase}."
                )

        existing = self._get_existing(db, workflow, project_id, t)
        if existing:
            return existing

        rnd = self._get_round(db, workflow, project_id, t)
        if not rnd:
            raise ValueError("Round not found.")
        if not rnd.is_locked:
            raise ValueError("Matching can be triggered only after round lock.")

        # -------------------------
        # DEFAULT LOGIC (SALEABLE / SLUM)
        # -------------------------
        else:
            min_ask = self._select_min_ask(
                db, workflow=workflow, project_id=project_id, t=t
            )
            max_quote = self._select_max_quote(
                db, workflow=workflow, project_id=project_id, t=t
            )

            notes = {
                "rule": "min(Ask.total_ask_inr) ↔ max(Quote.qbundle_inr)",
                "tiebreak": "id asc",
            }

            if not min_ask:
                notes["reason"] = "no_locked_asks_with_total"
            else:
                selected_ask_id, min_ask_val = min_ask

            if not max_quote:
                notes["reason_quote"] = "no_locked_quotes_with_qbundle"
            else:
                selected_quote_id, max_quote_val = max_quote

            if min_ask_val is not None and max_quote_val is not None:
                matched = Decimal(str(max_quote_val)) >= Decimal(str(min_ask_val))
                notes["condition"] = "max_quote_inr >= min_ask_total_inr"

        row = MatchingResult(
            workflow=workflow,
            project_id=project_id,
            round_id=rnd.id,
            t=t,
            status="computed",
            matched=matched,
            selected_ask_bid_id=selected_ask_id,
            selected_quote_bid_id=selected_quote_id,
            min_ask_total_inr=min_ask_val,
            max_quote_inr=max_quote_val,
            notes_json=notes,
        )

        db.add(row)
        db.commit()
        db.refresh(row)
        return row
