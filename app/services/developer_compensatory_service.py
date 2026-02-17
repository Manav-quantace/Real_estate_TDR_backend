from __future__ import annotations

import uuid
from typing import Optional, Tuple, Dict, Any
from decimal import Decimal

from sqlalchemy import select, asc
from sqlalchemy.orm import Session

from app.models.round import Round
from app.models.ask_bid import AskBid
from app.models.settlement_result import SettlementResult
from app.models.event_log import EventLog
from app.models.developer_default_event import DeveloperDefaultEvent
from app.models.developer_compensatory_event import DeveloperCompensatoryEvent


class DeveloperCompensatoryService:
    def _get_round(self, db: Session, workflow: str, project_id: uuid.UUID, t: int) -> Optional[Round]:
        return db.execute(
            select(Round).where(Round.workflow == workflow, Round.project_id == project_id, Round.t == t)
        ).scalar_one_or_none()

    def _get_settlement(self, db: Session, workflow: str, project_id: uuid.UUID, t: int) -> Optional[SettlementResult]:
        return db.execute(
            select(SettlementResult).where(
                SettlementResult.workflow == workflow,
                SettlementResult.project_id == project_id,
                SettlementResult.t == t,
            )
        ).scalar_one_or_none()

    def _get_existing_default(self, db: Session, workflow: str, project_id: uuid.UUID, t: int) -> Optional[DeveloperDefaultEvent]:
        return db.execute(
            select(DeveloperDefaultEvent).where(
                DeveloperDefaultEvent.workflow == workflow,
                DeveloperDefaultEvent.project_id == project_id,
                DeveloperDefaultEvent.t == t,
            )
        ).scalar_one_or_none()

    def _get_existing_comp(self, db: Session, workflow: str, project_id: uuid.UUID, t: int) -> Optional[DeveloperCompensatoryEvent]:
        return db.execute(
            select(DeveloperCompensatoryEvent).where(
                DeveloperCompensatoryEvent.workflow == workflow,
                DeveloperCompensatoryEvent.project_id == project_id,
                DeveloperCompensatoryEvent.t == t,
            )
        ).scalar_one_or_none()

    def _log(self, db: Session, *, workflow: str, project_id: uuid.UUID, t: int, actor: str, event_type: str, payload: Dict[str, Any]) -> None:
        db.add(EventLog(
            workflow=workflow,
            project_id=project_id,
            t=t,
            event_type=event_type,
            actor_participant_id=actor,
            payload_json=payload,
        ))

    def declare_developer_default(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
        declared_by_participant_id: str,
        reason: Optional[str],
    ) -> DeveloperDefaultEvent:
        rnd = self._get_round(db, workflow, project_id, t)
        if not rnd:
            raise ValueError("Round not found.")
        if not rnd.is_locked:
            raise ValueError("Developer default can be declared only after round lock.")

        settlement = self._get_settlement(db, workflow, project_id, t)
        if not settlement or not settlement.winning_ask_bid_id:
            raise ValueError("No winning developer ask exists; cannot declare developer default.")

        existing = self._get_existing_default(db, workflow, project_id, t)
        if existing:
            return existing

        ev = DeveloperDefaultEvent(
            workflow=workflow,
            project_id=project_id,
            round_id=settlement.round_id,
            t=t,
            winning_ask_bid_id=settlement.winning_ask_bid_id,
            declared_by_participant_id=declared_by_participant_id,
            reason=reason,
        )
        db.add(ev)
        self._log(
            db,
            workflow=workflow,
            project_id=project_id,
            t=t,
            actor=declared_by_participant_id,
            event_type="DEV_DEFAULT_DECLARED",
            payload={
                "winning_ask_bid_id": str(settlement.winning_ask_bid_id),
                "reason": reason,
            },
        )
        db.commit()
        db.refresh(ev)
        return ev

    def _next_eligible_min_ask(
        self,
        db: Session,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
        exclude_ask_bid_id: uuid.UUID,
    ) -> Optional[Tuple[uuid.UUID, Decimal]]:
        row = db.execute(
            select(AskBid.id, AskBid.total_ask_inr)
            .where(
                AskBid.workflow == workflow,
                AskBid.project_id == project_id,
                AskBid.t == t,
                AskBid.state == "locked",
                AskBid.total_ask_inr.is_not(None),
                AskBid.id != exclude_ask_bid_id,
            )
            .order_by(asc(AskBid.total_ask_inr), asc(AskBid.id))
            .limit(1)
        ).one_or_none()
        if not row:
            return None
        return row[0], Decimal(str(row[1]))

    def compute_and_store_if_needed(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
        actor_participant_id: str,
    ) -> DeveloperCompensatoryEvent:
        existing = self._get_existing_comp(db, workflow, project_id, t)
        if existing:
            return existing

        default_ev = self._get_existing_default(db, workflow, project_id, t)
        if not default_ev:
            raise ValueError("No developer default recorded; compensatory developer reallocation not applicable.")

        rnd = self._get_round(db, workflow, project_id, t)
        if not rnd or not rnd.is_locked:
            raise ValueError("Round must be locked.")

        settlement = self._get_settlement(db, workflow, project_id, t)
        if not settlement or not settlement.winning_ask_bid_id:
            raise ValueError("Settlement missing winning developer ask reference.")

        original_ask_id = settlement.winning_ask_bid_id

        # Load original ask bid to reference two-tier compensatory fields
        original_ask = db.execute(select(AskBid).where(AskBid.id == original_ask_id)).scalar_one_or_none()
        if not original_ask:
            raise ValueError("Original winning ask bid not found.")

        next_min = self._next_eligible_min_ask(db, workflow, project_id, t, exclude_ask_bid_id=original_ask_id)

        notes: Dict[str, Any] = {
            "trigger": "developer_default_event",
            "rule": "transfer rights to next eligible developer (min Ask.total_ask_inr among remaining locked asks)",
            "two_tier_reference": "use stored compensatory ask fields from original ask bid",
            "original_ask_bid_id": str(original_ask_id),
        }

        if not next_min:
            row = DeveloperCompensatoryEvent(
                workflow=workflow,
                project_id=project_id,
                round_id=settlement.round_id,
                t=t,
                settlement_result_id=settlement.id,
                developer_default_event_id=default_ev.id,
                status="no_transfer_no_eligible_developers",
                original_winning_ask_bid_id=original_ask_id,
                original_min_ask_total_inr=original_ask.total_ask_inr,
                new_winning_ask_bid_id=None,
                new_min_ask_total_inr=None,
                comp_dcu_units=original_ask.comp_dcu_units,
                comp_ask_price_per_unit_inr=original_ask.comp_ask_price_per_unit_inr,
                notes_json={**notes, "result": "no_other_locked_asks"},
            )
            db.add(row)
            self._log(
                db,
                workflow=workflow,
                project_id=project_id,
                t=t,
                actor=actor_participant_id,
                event_type="DEV_COMPENSATORY_COMPUTED",
                payload={"status": "no_transfer_no_eligible_developers"},
            )
            db.commit()
            db.refresh(row)
            return row

        new_ask_id, new_ask_total = next_min

        row = DeveloperCompensatoryEvent(
            workflow=workflow,
            project_id=project_id,
            round_id=settlement.round_id,
            t=t,
            settlement_result_id=settlement.id,
            developer_default_event_id=default_ev.id,
            status="computed",
            original_winning_ask_bid_id=original_ask_id,
            original_min_ask_total_inr=original_ask.total_ask_inr,
            new_winning_ask_bid_id=new_ask_id,
            new_min_ask_total_inr=new_ask_total,
            comp_dcu_units=original_ask.comp_dcu_units,
            comp_ask_price_per_unit_inr=original_ask.comp_ask_price_per_unit_inr,
            notes_json={**notes, "new_ask_bid_id": str(new_ask_id)},
        )
        db.add(row)

        self._log(
            db,
            workflow=workflow,
            project_id=project_id,
            t=t,
            actor=actor_participant_id,
            event_type="DEV_COMPENSATORY_TRANSFER",
            payload={
                "original_winning_ask_bid_id": str(original_ask_id),
                "new_winning_ask_bid_id": str(new_ask_id),
                "compensatory_reference": {
                    "comp_dcu_units": str(original_ask.comp_dcu_units) if original_ask.comp_dcu_units is not None else None,
                    "comp_ask_price_per_unit_inr": str(original_ask.comp_ask_price_per_unit_inr) if original_ask.comp_ask_price_per_unit_inr is not None else None,
                },
            },
        )

        db.commit()
        db.refresh(row)
        return row
