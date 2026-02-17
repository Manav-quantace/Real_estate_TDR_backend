#app/services/subsidized_valuer_service.py
from __future__ import annotations

import uuid
from typing import Optional, List
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.subsidized_valuation import SubsidizedValuationRecord


class SubsidizedValuerService:
    def _require_subsidized_project(self, db: Session, project_id: uuid.UUID) -> Project:
        proj = db.execute(select(Project).where(Project.id == project_id, Project.workflow == "subsidized")).scalar_one_or_none()
        if not proj:
            raise ValueError("Subsidized project not found.")
        return proj

    def _next_version(self, db: Session, workflow: str, project_id: uuid.UUID) -> int:
        mx = db.execute(
            select(func.max(SubsidizedValuationRecord.version)).where(
                SubsidizedValuationRecord.workflow == workflow,
                SubsidizedValuationRecord.project_id == project_id,
            )
        ).scalar_one_or_none()
        return int(mx or 0) + 1

    def get_latest(self, db: Session, *, workflow: str, project_id: uuid.UUID) -> Optional[SubsidizedValuationRecord]:
        return db.execute(
            select(SubsidizedValuationRecord)
            .where(SubsidizedValuationRecord.workflow == workflow, SubsidizedValuationRecord.project_id == project_id)
            .order_by(desc(SubsidizedValuationRecord.version))
            .limit(1)
        ).scalar_one_or_none()

    def list_all(self, db: Session, *, workflow: str, project_id: uuid.UUID, limit: int = 50) -> List[SubsidizedValuationRecord]:
        return db.execute(
            select(SubsidizedValuationRecord)
            .where(SubsidizedValuationRecord.workflow == workflow, SubsidizedValuationRecord.project_id == project_id)
            .order_by(desc(SubsidizedValuationRecord.version))
            .limit(limit)
        ).scalars().all()

    def submit_new_version(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        valuation_inr: float,
        status: str,
        signed_by_participant_id: str,
        verified_by_participant_id: Optional[str] = None,
    ) -> SubsidizedValuationRecord:
        if workflow != "subsidized":
            raise ValueError("workflow must be subsidized.")
        proj = self._require_subsidized_project(db, project_id)

        # Read-only after publish (strict)
        if proj.is_published:
            raise ValueError("Valuation is read-only after project publish.")

        version = self._next_version(db, workflow, project_id)

        row = SubsidizedValuationRecord(
            workflow=workflow,
            project_id=project_id,
            version=version,
            valuation_inr=valuation_inr,
            status=status,
            signed_by_participant_id=signed_by_participant_id,
            verified_by_participant_id=verified_by_participant_id if status == "verified" else None,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
