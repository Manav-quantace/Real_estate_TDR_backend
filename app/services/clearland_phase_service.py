# app/services/clearland_phase_service.py
from __future__ import annotations

import uuid
from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.clearland_phase import ClearlandPhase
from app.models.project import Project
from app.core.clearland_phases import ClearlandPhaseType


def _now():
    return datetime.now(timezone.utc)


class ClearlandPhaseService:
    """
    Service to read and transition Clearland project phases.

    Public methods:
    - get_current_phase(db, project_id) -> Optional[ClearlandPhase]
    - get_current(db, project_id) -> alias for get_current_phase (compatibility)
    - history(db, project_id) -> List[ClearlandPhase] (ordered by effective_from asc)
    - transition(db, project_id, target_phase, actor_participant_id, notes) -> ClearlandPhase
    """

    def get_current_phase(
        self,
        db: Session,
        *,
        project_id: uuid.UUID,
    ) -> Optional[ClearlandPhase]:
        """
        Returns the active clearland phase for a project.
        Active = effective_to IS NULL
        """
        return db.execute(
            select(ClearlandPhase)
            .where(
                ClearlandPhase.project_id == project_id,
                ClearlandPhase.effective_to.is_(None),
            )
            .order_by(ClearlandPhase.effective_from.desc())
            .limit(1)
        ).scalar_one_or_none()

    # back-compat alias
    def get_current(self, db: Session, *, project_id: uuid.UUID) -> Optional[ClearlandPhase]:
        return self.get_current_phase(db, project_id=project_id)

    def history(self, db: Session, project_id: uuid.UUID) -> List[ClearlandPhase]:
        """
        Return full phase history for a project in ascending time order (earliest -> latest).
        Useful for UI timeline.
        """
        rows = db.execute(
            select(ClearlandPhase)
            .where(ClearlandPhase.project_id == project_id)
            .order_by(ClearlandPhase.effective_from.asc())
        ).scalars().all()
        return rows

    def transition(
        self,
        db: Session,
        *,
        project_id: uuid.UUID,
        target_phase: ClearlandPhaseType,
        actor_participant_id: str,
        notes: dict | None = None,
    ) -> ClearlandPhase:
        """
        Concurrency-safe, authority-driven phase transition.

        Guarantees:
        - Only one active phase per project
        - Idempotent if target == current
        - Serialized per project using FOR UPDATE
        """

        now = _now()

        # 🔒 SERIALIZE PER PROJECT
        # This prevents concurrent transitions for the same project
        db.execute(
            select(Project)
            .where(Project.id == project_id)
            .with_for_update()
        ).scalar_one()

        # Re-read current phase under lock
        current = self.get_current_phase(db, project_id=project_id)
        if current and current.phase == target_phase.value:
            return current  # idempotent

        # Close existing active phase
        db.execute(
            update(ClearlandPhase)
            .where(
                ClearlandPhase.project_id == project_id,
                ClearlandPhase.effective_to.is_(None),
            )
            .values(effective_to=now)
        )

        # Insert new phase
        row = ClearlandPhase(
            project_id=project_id,
            phase=target_phase.value,
            created_by_participant_id=actor_participant_id,
            notes_json=notes or {},
            effective_from=now,
        )

        db.add(row)
        db.commit()
        db.refresh(row)
        return row