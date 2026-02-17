from __future__ import annotations

import uuid
from typing import Dict, Any, Iterable, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.models.audit_log import AuditLogRecord
from app.policies.export_policy import ExportScope


AUDIT_FIELDS = [
    "id", "created_at", "request_id", "route", "method",
    "actor_participant_id", "actor_role",
    "workflow", "project_id", "t",
    "action", "status",
    "payload_hash", "ref_id",
]


class ExportAuditService:
    def iter_rows(
        self,
        db: Session,
        *,
        scope: ExportScope,
        workflow: str,
        project_id: uuid.UUID,
        limit: int = 100000,
    ) -> Iterable[Dict[str, Any]]:
        stmt = select(AuditLogRecord).where(
            AuditLogRecord.workflow == workflow,
            AuditLogRecord.project_id == project_id,
        )
        if not scope.allow_full:
            stmt = stmt.where(AuditLogRecord.actor_participant_id == scope.participant_id)

        stmt = stmt.order_by(desc(AuditLogRecord.created_at)).limit(limit)

        for r in db.execute(stmt).scalars().yield_per(1000):
            yield {
                "id": str(r.id),
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "request_id": r.request_id,
                "route": r.route,
                "method": r.method,
                "actor_participant_id": r.actor_participant_id,
                "actor_role": r.actor_role,
                "workflow": r.workflow,
                "project_id": str(r.project_id),
                "t": r.t,
                "action": r.action,
                "status": r.status,
                "payload_hash": r.payload_hash,
                "ref_id": r.ref_id,
            }

    def fieldnames(self) -> List[str]:
        return AUDIT_FIELDS
