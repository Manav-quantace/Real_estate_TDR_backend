#app/api/v1/subsidized_valuer.py
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth_deps import get_current_principal
from app.policies.rbac import Principal

from app.schemas.subsidized_valuer import (
    SubsidizedValuationUpsertRequest,
    SubsidizedValuationHistoryResponse,
)
from app.services.subsidized_valuer_service import SubsidizedValuerService
from app.services.audit_service import audit_event

router = APIRouter(prefix="/subsidized")


def _iso(dt):
    return dt.isoformat() if dt else None


def _to_resp(row):
    return {
        "workflow": row.workflow,
        "projectId": str(row.project_id),
        "version": row.version,
        "valuationInr": str(row.valuation_inr) if row.valuation_inr is not None else None,
        "status": row.status,
        "valuedAtIso": _iso(row.valued_at),
        "signedByParticipantId": row.signed_by_participant_id,
        "verifiedAtIso": _iso(row.verified_at),
        "verifiedByParticipantId": row.verified_by_participant_id,
    }


def _require_valuer_role(principal: Principal) -> None:
    # Keep strict & consistent with existing roles.
    # If you later add INDEPENDENT_VALUER as a role, change it here only.
    if principal.role.value not in {"GOV_AUTHORITY", "AUDITOR"}:
        raise PermissionError("Only GOV_AUTHORITY or AUDITOR may submit/verify valuer valuations.")


@router.post("/valuer")
async def submit_valuer_valuation(
    request: Request,
    body: SubsidizedValuationUpsertRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    if body.workflow.value != "subsidized":
        raise HTTPException(status_code=400, detail="workflow must be subsidized.")
    try:
        _require_valuer_role(principal)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    try:
        pid = uuid.UUID(body.projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    svc = SubsidizedValuerService()
    try:
        row = svc.submit_new_version(
            db,
            workflow="subsidized",
            project_id=pid,
            valuation_inr=float(body.valuationInr),
            status=body.status,
            signed_by_participant_id=principal.participant_id,
            verified_by_participant_id=principal.participant_id if body.status == "verified" else None,
        )
    except ValueError as e:
        msg = str(e)
        code = 409 if "read-only" in msg else 400
        raise HTTPException(status_code=code, detail=msg)

    # Audit every change (safe summary only)
    audit_event(
        db,
        request=request,
        actor_participant_id=principal.participant_id,
        actor_role=principal.role.value,
        workflow="subsidized",
        project_id=pid,
        t=None,
        action="SUBSIDIZED_VALUATION_SUBMITTED",
        payload_summary={
            "projectId": str(pid),
            "workflow": "subsidized",
            "version": row.version,
            "status": row.status,
            "valuation_inr": str(row.valuation_inr),
        },
        ref_id=str(row.id),
    )

    return {"status": "ok", "record": _to_resp(row)}


@router.get("/valuer", response_model=SubsidizedValuationHistoryResponse)
async def get_valuer_valuation(
    workflow: str = Query(..., min_length=1),
    projectId: str = Query(..., min_length=1),
    includeHistory: bool = Query(default=False),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    if workflow != "subsidized":
        raise HTTPException(status_code=400, detail="workflow must be subsidized.")
    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    svc = SubsidizedValuerService()
    latest = svc.get_latest(db, workflow="subsidized", project_id=pid)

    history = []
    if includeHistory:
        history = svc.list_all(db, workflow="subsidized", project_id=pid, limit=100)

    return {
        "workflow": "subsidized",
        "projectId": projectId,
        "latest": _to_resp(latest) if latest else None,
        "history": [_to_resp(r) for r in history] if includeHistory else [],
    }