from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps_params import require_workflow_project_scope
from app.core.auth_deps import get_current_principal
from app.policies.rbac import Principal
from app.schemas.events import DefaultDeclareRequest, PenaltyEventResponse
from app.services.penalty_service import PenaltyService

router = APIRouter(prefix="/events")


def _iso(dt):
    return dt.isoformat() if dt else None


def _require_authority(principal: Principal) -> None:
    if principal.role.value not in {"GOV_AUTHORITY", "AUDITOR"}:
        raise PermissionError("Only authority/auditor may declare defaults.")


@router.post("/default", dependencies=[Depends(require_workflow_project_scope)])
async def declare_default(
    request: Request,
    body: DefaultDeclareRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    # strict scope
    if body.workflow.value != request.state.workflow or body.projectId != request.state.project_id:
        raise HTTPException(status_code=400, detail="Payload scope mismatch.")

    try:
        _require_authority(principal)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    workflow = request.state.workflow
    pid_raw = request.state.project_id
    try:
        project_uuid = uuid.UUID(pid_raw)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    svc = PenaltyService()
    try:
        ev = svc.declare_default(
            db,
            workflow=workflow,
            project_id=project_uuid,
            t=body.t,
            declared_by_participant_id=principal.participant_id,
            reason=body.reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {
        "status": "default_recorded",
        "defaultEventId": str(ev.id),
        "workflow": workflow,
        "projectId": pid_raw,
        "t": body.t,
    }


@router.get("/penalty", response_model=PenaltyEventResponse, dependencies=[Depends(require_workflow_project_scope)])
async def get_penalty_event(
    request: Request,
    t: int = Query(..., ge=0),
    db: Session = Depends(get_db),
):
    workflow = request.state.workflow
    pid_raw = request.state.project_id
    try:
        project_uuid = uuid.UUID(pid_raw)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    svc = PenaltyService()
    try:
        row = svc.compute_and_store_penalty_if_needed(db, workflow=workflow, project_id=project_uuid, t=t)
    except ValueError as e:
        # deterministic: if no default recorded, penalty not applicable
        msg = str(e)
        if "No default recorded" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=409, detail=msg)

    return {
        "workflow": workflow,
        "projectId": pid_raw,
        "t": t,
        "winner_quote_bid_id": str(row.winner_quote_bid_id),
        "second_price_quote_bid_id": str(row.second_price_quote_bid_id),
        "bmax_inr": str(row.bmax_inr),
        "bsecond_inr": str(row.bsecond_inr),
        "penalty_inr": str(row.penalty_inr),
        "enforcement_status": row.enforcement_status,
        "computed_at_iso": _iso(row.computed_at),
        "notes": row.notes_json or {},
    }
