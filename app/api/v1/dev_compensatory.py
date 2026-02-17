from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps_params import require_workflow_project_scope
from app.core.auth_deps import get_current_principal
from app.policies.rbac import Principal
from app.schemas.dev_compensatory import DeveloperDefaultDeclareRequest, DeveloperCompensatoryEventResponse


router = APIRouter(prefix="/events/developer")


def _iso(dt):
    return dt.isoformat() if dt else None


def _require_authority(principal: Principal) -> None:
    if principal.role.value not in {"GOV_AUTHORITY", "AUDITOR"}:
        raise PermissionError("Only authority/auditor may declare developer default.")


@router.post("/default", dependencies=[Depends(require_workflow_project_scope)])
async def declare_developer_default(
    request: Request,
    body: DeveloperDefaultDeclareRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    if body.workflow.value != request.state.workflow or body.projectId != request.state.project_id:
        raise HTTPException(status_code=400, detail="Payload scope mismatch.")

    try:
        _require_authority(principal)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    workflow = request.state.workflow
    try:
        project_uuid = uuid.UUID(request.state.project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    svc = DeveloperCompensatoryService()
    try:
        ev = svc.declare_developer_default(
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
        "status": "developer_default_recorded",
        "developerDefaultEventId": str(ev.id),
        "workflow": workflow,
        "projectId": request.state.project_id,
        "t": body.t,
    }


@router.get("/compensatory", response_model=DeveloperCompensatoryEventResponse, dependencies=[Depends(require_workflow_project_scope)])
async def get_developer_compensatory(
    request: Request,
    t: int = Query(..., ge=0),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    workflow = request.state.workflow
    try:
        project_uuid = uuid.UUID(request.state.project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    svc = DeveloperCompensatoryService()
    try:
        row = svc.compute_and_store_if_needed(
            db,
            workflow=workflow,
            project_id=project_uuid,
            t=t,
            actor_participant_id=principal.participant_id,
        )
    except ValueError as e:
        msg = str(e)
        if "No developer default recorded" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=409, detail=msg)

    return {
        "workflow": workflow,
        "projectId": request.state.project_id,
        "t": t,
        "status": row.status,
        "computed_at_iso": _iso(row.computed_at),

        "original_winning_ask_bid_id": str(row.original_winning_ask_bid_id),
        "original_min_ask_total_inr": str(row.original_min_ask_total_inr) if row.original_min_ask_total_inr is not None else None,

        "new_winning_ask_bid_id": str(row.new_winning_ask_bid_id) if row.new_winning_ask_bid_id else None,
        "new_min_ask_total_inr": str(row.new_min_ask_total_inr) if row.new_min_ask_total_inr is not None else None,

        "comp_dcu_units": str(row.comp_dcu_units) if row.comp_dcu_units is not None else None,
        "comp_ask_price_per_unit_inr": str(row.comp_ask_price_per_unit_inr) if row.comp_ask_price_per_unit_inr is not None else None,

        "notes": row.notes_json or {},
    }