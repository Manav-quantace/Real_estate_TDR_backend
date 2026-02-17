# app/services/rounds_service.py
# app/services/rounds_service.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, desc
from sqlalchemy.orm import Session

from app.models.round import Round
from app.models.enums import RoundState
from app.services.bids_service import BidService

# ✅ Clearland imports
from app.services.clearland_phase_service import ClearlandPhaseService
from app.core.clearland_phases import ClearlandPhaseType


def _now():
    return datetime.now(timezone.utc)


class RoundService:
    # ---------------------------
    # READS
    # ---------------------------

    def get_current_round(
        self,
        db: Session,
        workflow: str,
        project_id: uuid.UUID,
    ) -> Optional[Round]:
        """
        Returns the latest round (highest t) or None.
        """
        return (
            db.execute(
                select(Round)
                .where(
                    Round.workflow == workflow,
                    Round.project_id == project_id,
                )
                .order_by(desc(Round.t))
            )
            .scalars()
            .first()
        )

    def get_round_for_update(
        self,
        db: Session,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
    ) -> Optional[Round]:
        """
        Lock a specific round row (FOR UPDATE).
        """
        return (
            db.execute(
                select(Round)
                .where(
                    Round.workflow == workflow,
                    Round.project_id == project_id,
                    Round.t == t,
                )
                .with_for_update()
            )
            .scalars()
            .one_or_none()
        )

    def get_latest_round_for_update(
        self,
        db: Session,
        workflow: str,
        project_id: uuid.UUID,
    ) -> Optional[Round]:
        """
        Lock the latest round row to serialize transitions.
        """
        return (
            db.execute(
                select(Round)
                .where(
                    Round.workflow == workflow,
                    Round.project_id == project_id,
                )
                .order_by(desc(Round.t))
                .with_for_update()
            )
            .scalars()
            .first()
        )

    # ---------------------------
    # MUTATIONS
    # ---------------------------

    def open_next_round(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        window_start: Optional[datetime],
        window_end: Optional[datetime],
    ) -> Round:
        """
        Rules:
        - If no round exists → create t=0 (open)
        - If latest exists:
            - If open → ❌ forbidden
            - If t=0 AND draft → ✅ open it
            - If not locked → ❌ forbidden
            - If locked → create t+1
        """

        # ✅ CLEARLAND PHASE GUARD (NO EFFECT ON OTHER WORKFLOWS)
        if workflow == "clearland":
            phase = ClearlandPhaseService().get_current_phase(
                db, project_id=project_id
            )
            if not phase:
                raise ValueError("Clearland phase not initialized.")

            if phase.phase not in {
                ClearlandPhaseType.DEVELOPER_ASK_OPEN.value,
                ClearlandPhaseType.BUYER_BIDDING_OPEN.value,
            }:
                raise ValueError(
                    f"Cannot open round during clearland phase {phase.phase}."
                )

        latest = self.get_latest_round_for_update(db, workflow, project_id)

        # ───────────────────────────────
        # CASE 1: No rounds yet
        # ───────────────────────────────
        if not latest:
            r = Round(
                workflow=workflow,
                project_id=project_id,
                t=0,
                state=RoundState.draft.value,
                bidding_window_start=window_start or _now(),
                bidding_window_end=window_end,
                is_open=True,
                is_locked=False,
            )
            db.add(r)
            db.commit()
            db.refresh(r)
            return r

        # ───────────────────────────────
        # CASE 2: Round 0 special open
        # ───────────────────────────────
        if (
            latest.t == 0
            and not latest.is_open
            and not latest.is_locked
            and latest.state == RoundState.draft.value
        ):
            latest.is_open = True
            latest.bidding_window_start = window_start or _now()
            latest.bidding_window_end = window_end
            latest.updated_at = _now()
            db.commit()
            db.refresh(latest)
            return latest

        # ───────────────────────────────
        # CASE 3: Normal progression
        # ───────────────────────────────
        if latest.is_open:
            raise ValueError("Cannot open a new round while a round is open.")
        if not latest.is_locked:
            raise ValueError("Cannot open a new round until the latest round is locked.")

        next_t = latest.t + 1

        r = Round(
            workflow=workflow,
            project_id=project_id,
            t=next_t,
            state=RoundState.draft.value,
            bidding_window_start=window_start or _now(),
            bidding_window_end=window_end,
            is_open=True,
            is_locked=False,
        )

        db.add(r)
        db.commit()
        db.refresh(r)
        return r

    def close_round(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
    ) -> Round:
        rnd = self.get_round_for_update(db, workflow, project_id, t)
        if not rnd:
            raise ValueError("Round not found.")
        if rnd.is_locked:
            raise ValueError("Cannot close a locked round.")
        if not rnd.is_open:
            raise ValueError("Round is already closed.")

        rnd.is_open = False
        rnd.state = RoundState.submitted.value
        rnd.updated_at = _now()

        db.commit()
        db.refresh(rnd)
        return rnd

    def lock_round(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
        actor_participant_id: Optional[str] = None,
    ) -> Round:
        """
        FINAL operation:
        - Round must be closed
        - Locks ALL bids
        - Locks the round
        """
        rnd = self.get_round_for_update(db, workflow, project_id, t)
        if not rnd:
            raise ValueError("Round not found.")
        if rnd.is_locked:
            return rnd
        if rnd.is_open:
            raise ValueError("Round must be closed before locking.")

        # 🔒 LOCK ALL BIDS FIRST (CRITICAL)
        BidService().lock_all_bids_for_round(
            db,
            workflow=workflow,
            project_id=project_id,
            t=t,
            actor_participant_id=actor_participant_id,
        )

        # 🔒 LOCK ROUND
        rnd.is_locked = True
        rnd.state = RoundState.locked.value
        rnd.updated_at = _now()

        db.commit()
        db.refresh(rnd)
        return rnd
