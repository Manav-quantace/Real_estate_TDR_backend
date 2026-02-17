# app/services/slum_state_machine.py
# app/services/slum_state_machine.py
from __future__ import annotations

import uuid
from typing import Optional, Dict, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.project import Project
from app.models.slum_portal_membership import SlumPortalMembership
from app.models.slum_consent import SlumConsent
from app.models.round import Round
from app.models.ask_bid import AskBid
from app.models.quote_bid import QuoteBid

from app.services.rounds_service import RoundService
from app.services.matching_service import MatchingService
from app.services.settlement_service import SettlementService

from app.models.enums import RoundState
from app.core.slum_types import SlumPortalType


class SlumStateMachine:
    """
    Book-faithful orchestration layer for SLUM workflow.

    Responsibilities:
    - Enforce tripartite structure
    - Enforce slum dweller consent
    - Enforce economic readiness
    - Gate round lifecycle
    - Gate matching
    - Gate settlement
    """

    REQUIRED_PORTALS: Set[str] = {
        SlumPortalType.SLUM_DWELLER.value,
        SlumPortalType.SLUM_LAND_DEVELOPER.value,
        SlumPortalType.AFFORDABLE_HOUSING_DEV.value,
    }

    # ─────────────────────────────────────────────
    # INTERNAL READ HELPERS
    # ─────────────────────────────────────────────

    def _get_project(self, db: Session, project_id: uuid.UUID) -> Project:
        proj = db.execute(
            select(Project).where(Project.workflow == "slum", Project.id == project_id)
        ).scalar_one_or_none()
        if not proj:
            raise ValueError("Slum project not found.")
        return proj

    def _get_portals(self, db: Session, project_id: uuid.UUID) -> Set[str]:
        rows = db.execute(
            select(SlumPortalMembership.portal_type).where(
                SlumPortalMembership.workflow == "slum",
                SlumPortalMembership.project_id == project_id,
            )
        ).scalars().all()
        return set(rows or [])

    def _get_round(self, db: Session, project_id: uuid.UUID, t: int) -> Round:
        rnd = db.execute(
            select(Round).where(
                Round.workflow == "slum",
                Round.project_id == project_id,
                Round.t == t,
            )
        ).scalar_one_or_none()
        if not rnd:
            raise ValueError("Round not found.")
        return rnd

    # ─────────────────────────────────────────────
    # INVARIANTS (BOOK RULES)
    # ─────────────────────────────────────────────

    def assert_tripartite_ready(self, db: Session, project_id: uuid.UUID) -> None:
        portals = self._get_portals(db, project_id)
        missing = self.REQUIRED_PORTALS - portals
        if missing:
            raise ValueError(f"Missing required slum portals: {missing}")

    def assert_slum_dwellers_consented(self, db: Session, project_id: uuid.UUID) -> None:
        rows = db.execute(
            select(SlumConsent.participant_id).where(
                SlumConsent.workflow == "slum",
                SlumConsent.project_id == project_id,
                SlumConsent.portal_type == SlumPortalType.SLUM_DWELLER.value,
                SlumConsent.agreed == True,
            )
        ).scalars().all()

        if not rows:
            raise ValueError("No slum dweller has given consent.")

    def assert_bids_exist(self, db: Session, project_id: uuid.UUID, t: int) -> None:
        ask_exists = db.execute(
            select(AskBid.id).where(
                AskBid.workflow == "slum",
                AskBid.project_id == project_id,
                AskBid.t == t,
                AskBid.state == "locked",
            )
        ).first()

        quote_exists = db.execute(
            select(QuoteBid.id).where(
                QuoteBid.workflow == "slum",
                QuoteBid.project_id == project_id,
                QuoteBid.t == t,
                QuoteBid.state == "locked",
            )
        ).first()

        if not ask_exists or not quote_exists:
            raise ValueError(
                "Settlement requires at least one locked ask and one locked quote."
            )

    # ─────────────────────────────────────────────
    # ROUND CONTROL
    # ─────────────────────────────────────────────

    def open_round_if_allowed(
        self,
        db: Session,
        *,
        project_id: uuid.UUID,
        window_start=None,
        window_end=None,
    ) -> Round:
        """
        Rules:
        - Tripartite portals must exist
        - Slum dwellers must have consented
        """
        self.assert_tripartite_ready(db, project_id)
        self.assert_slum_dwellers_consented(db, project_id)

        return RoundService().open_next_round(
            db,
            workflow="slum",
            project_id=project_id,
            window_start=window_start,
            window_end=window_end,
        )

    def close_round(
        self,
        db: Session,
        *,
        project_id: uuid.UUID,
        t: int,
    ) -> Round:
        return RoundService().close_round(
            db,
            workflow="slum",
            project_id=project_id,
            t=t,
        )

    def lock_round(
        self,
        db: Session,
        *,
        project_id: uuid.UUID,
        t: int,
        actor_participant_id: Optional[str],
    ) -> Round:
        return RoundService().lock_round(
            db,
            workflow="slum",
            project_id=project_id,
            t=t,
            actor_participant_id=actor_participant_id,
        )

    # ─────────────────────────────────────────────
    # MATCHING GATE
    # ─────────────────────────────────────────────

    def run_matching(
        self,
        db: Session,
        *,
        project_id: uuid.UUID,
        t: int,
    ):
        rnd = self._get_round(db, project_id, t)

        if not rnd.is_locked:
            raise ValueError("Round must be locked before matching.")

        return MatchingService().compute_and_store_if_needed(
            db,
            workflow="slum",
            project_id=project_id,
            t=t,
        )

    # ─────────────────────────────────────────────
    # SETTLEMENT GATE
    # ─────────────────────────────────────────────

    def run_settlement(
        self,
        db: Session,
        *,
        project_id: uuid.UUID,
        t: int,
    ):
        """
        Rules:
        - Tripartite portals must exist
        - Slum dwellers must have consented
        - Round must be locked
        - There must be bids
        """

        self.assert_tripartite_ready(db, project_id)
        self.assert_slum_dwellers_consented(db, project_id)

        rnd = self._get_round(db, project_id, t)
        if not rnd.is_locked:
            raise ValueError("Round must be locked before settlement.")

        self.assert_bids_exist(db, project_id, t)

        return SettlementService().compute_and_store_if_needed(
            db,
            workflow="slum",
            project_id=project_id,
            t=t,
        )

    # ─────────────────────────────────────────────
    # STATUS INTROSPECTION
    # ─────────────────────────────────────────────

    def get_slum_status(
        self,
        db: Session,
        *,
        project_id: uuid.UUID,
    ) -> Dict[str, Any]:
        proj = self._get_project(db, project_id)
        portals = self._get_portals(db, project_id)

        round_ = RoundService().get_current_round(
            db,
            workflow="slum",
            project_id=project_id,
        )

        return {
            "projectId": str(project_id),
            "published": proj.is_published,
            "tripartite_ready": portals == self.REQUIRED_PORTALS,
            "slum_consent_ready": bool(
                db.execute(
                    select(SlumConsent.id).where(
                        SlumConsent.workflow == "slum",
                        SlumConsent.project_id == project_id,
                        SlumConsent.portal_type == SlumPortalType.SLUM_DWELLER.value,
                        SlumConsent.agreed == True,
                    )
                ).first()
            ),
            "current_round": round_.t if round_ else None,
            "round_state": round_.state if round_ else None,
            "is_open": round_.is_open if round_ else False,
            "is_locked": round_.is_locked if round_ else False,
            "portals_present": list(portals),
        }
