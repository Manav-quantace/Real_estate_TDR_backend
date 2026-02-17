from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from app.db.session import get_db
from app.core.deps_params import require_workflow_project_scope
from app.schemas.audit import AuditLogListResponse
from app.models.audit_log import AuditLogRecord

router = APIRouter(prefix="/ledgeraudit")


def _iso(dt):
    return dt.isoformat() if dt else None


@router.get(
    "/audit",
    response_model=AuditLogListResponse,
    dependencies=[Depends(require_workflow_project_scope)],
)
async def get_audit_log(
    request: Request,
    t: int | None = Query(default=None, ge=0),
    limit: int = Query(default=200, ge=1, le=2000),
    db: Session = Depends(get_db),
):
    workflow = request.state.workflow
    pid_raw = request.state.project_id
    try:
        pid = uuid.UUID(pid_raw)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    stmt = select(AuditLogRecord).where(
        AuditLogRecord.workflow == workflow,
        AuditLogRecord.project_id == pid,
    )
    if t is not None:
        stmt = stmt.where(AuditLogRecord.t == t)

    stmt = stmt.order_by(desc(AuditLogRecord.created_at)).limit(limit)

    rows = db.execute(stmt).scalars().all()

    return {
        "workflow": workflow,
        "projectId": pid_raw,
        "t": t,
        "records": [
            {
                "id": str(r.id),
                "createdAtIso": _iso(r.created_at),
                "requestId": r.request_id,
                "route": r.route,
                "method": r.method,
                "actorParticipantId": r.actor_participant_id,
                "actorRole": r.actor_role,
                "workflow": r.workflow,
                "projectId": str(r.project_id),
                "t": r.t,
                "action": r.action,
                "status": r.status,
                "payloadHash": r.payload_hash,
                "payloadSummary": r.payload_summary_json or {},
                "refId": r.ref_id,
            }
            for r in rows
        ],
    }
