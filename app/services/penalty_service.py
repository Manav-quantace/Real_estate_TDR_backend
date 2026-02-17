#app/services/penalty_service.py
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.round import Round
from app.models.default_event import DefaultEvent
from app.models.penalty_event import PenaltyEvent
from app.models.settlement_result import SettlementResult
from app.services.settlement_service import SettlementService


class PenaltyService:
    def _get_round(self, db: Session, workflow: str, project_id: uuid.UUID, t: int) -> Optional[Round]:
        return db.execute(
            select(Round).where(Round.workflow == workflow, Round.project_id == project_id, Round.t == t)
        ).scalar_one_or_none()

    def _get_default(self, db: Session, workflow: str, project_id: uuid.UUID, t: int) -> Optional[DefaultEvent]:
        return db.execute(
            select(DefaultEvent).where(
                DefaultEvent.workflow == workflow,
                DefaultEvent.project_id == project_id,
                DefaultEvent.t == t,
            )
        ).scalar_one_or_none()

    def _get_penalty(self, db: Session, workflow: str, project_id: uuid.UUID, t: int) -> Optional[PenaltyEvent]:
        return db.execute(
            select(PenaltyEvent).where(
                PenaltyEvent.workflow == workflow,
                PenaltyEvent.project_id == project_id,
                PenaltyEvent.t == t,
            )
        ).scalar_one_or_none()

    def declare_default(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
        declared_by_participant_id: str,
        reason: str | None,
    ) -> DefaultEvent:
        rnd = self._get_round(db, workflow, project_id, t)
        if not rnd:
            raise ValueError("Round not found.")
        if not rnd.is_locked:
            raise ValueError("Default can be declared only after round lock.")

        # Ensure settlement exists (deterministic source of winner and bmax/bsecond)
        settlement = SettlementService().compute_and_store_if_needed(db, workflow=workflow, project_id=project_id, t=t)

        if not settlement.winner_quote_bid_id:
            raise ValueError("No winner exists; cannot declare default.")

        existing = self._get_default(db, workflow, project_id, t)
        if existing:
            return existing

        ev = DefaultEvent(
            workflow=workflow,
            project_id=project_id,
            round_id=settlement.round_id,
            t=t,
            winner_quote_bid_id=settlement.winner_quote_bid_id,
            declared_by_participant_id=declared_by_participant_id,
            reason=reason,
        )
        db.add(ev)
        db.commit()
        db.refresh(ev)
        return ev

    def compute_and_store_penalty_if_needed(self, db: Session, *, workflow: str, project_id: uuid.UUID, t: int) -> PenaltyEvent:
        existing = self._get_penalty(db, workflow, project_id, t)
        if existing:
            return existing

        default_ev = self._get_default(db, workflow, project_id, t)
        if not default_ev:
            raise ValueError("No default recorded; penalty not applicable.")

        settlement = db.execute(
            select(SettlementResult).where(
                SettlementResult.workflow == workflow,
                SettlementResult.project_id == project_id,
                SettlementResult.t == t,
            )
        ).scalar_one_or_none()

        if not settlement:
            raise ValueError("SettlementResult not found.")

        if settlement.winner_quote_bid_id is None or settlement.second_price_quote_bid_id is None:
            raise ValueError("Settlement missing winner or second-price reference; cannot compute penalty deterministically.")

        if settlement.max_quote_inr is None or settlement.second_price_inr is None:
            raise ValueError("Settlement missing bmax or bsecond; cannot compute penalty deterministically.")

        bmax = Decimal(str(settlement.max_quote_inr))
        bsecond = Decimal(str(settlement.second_price_inr))

        # EXACT formula
        penalty = bmax - bsecond

        notes = {
            "formula": "Pconfiscation = bmax − bsecond",
            "bmax_source": "SettlementResult.max_quote_inr",
            "bsecond_source": "SettlementResult.second_price_inr",
            "determinism": "values persisted from Vickrey settlement; penalty computed once and stored",
        }

        row = PenaltyEvent(
            workflow=workflow,
            project_id=project_id,
            round_id=settlement.round_id,
            t=t,
            settlement_result_id=settlement.id,
            default_event_id=default_ev.id,
            winner_quote_bid_id=settlement.winner_quote_bid_id,
            second_price_quote_bid_id=settlement.second_price_quote_bid_id,
            bmax_inr=bmax,
            bsecond_inr=bsecond,
            penalty_inr=penalty,
            enforcement_status="pending",
            notes_json=notes,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
