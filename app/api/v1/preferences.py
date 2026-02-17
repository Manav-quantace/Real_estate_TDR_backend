# app/api/v1/preferences.py
from __future__ import annotations
import uuid
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from app.core.deps import strict_workflow_scope
from app.core.auth_deps import get_current_principal
from app.db.session import get_db
from app.schemas.preferences import PreferenceBidPayload, MyPreferenceResponse
from app.schemas.bid_receipts import BidReceipt
from app.policies.rbac import ACTION_SUBMIT_PREFERENCES, require_action, Principal
from app.policies.preference_policies import (
    enforce_slum_workflow_only,
    enforce_slum_dweller_role,
)
from app.services.preferences_service import PreferencesService
from app.policies.clearland_phase_policy import enforce_phase_allows_action
from app.policies.clearland_membership_policy import enforce_active_clearland_membership

router = APIRouter(prefix="/bids")


def _receipt_id() -> str:
    return "RCP-" + secrets.token_hex(8).upper()


def _iso(dt):
    return dt.isoformat() if dt else None


@router.post(
    "/preferences",
    dependencies=[Depends(strict_workflow_scope)],
    response_model=BidReceipt,
)
async def post_preferences(
    request: Request,
    payload: PreferenceBidPayload,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    wf = request.state.workflow
    pid_raw = request.state.project_id

    try:
        require_action(principal, ACTION_SUBMIT_PREFERENCES)
        enforce_slum_dweller_role(principal)
        enforce_slum_workflow_only(wf)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    try:
        project_uuid = uuid.UUID(pid_raw)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    enforce_active_clearland_membership(
        db=db,
        workflow=wf,
        project_id=project_uuid,
        participant_id=principal.participant_id,
    )

    enforce_phase_allows_action(
        db=db,
        workflow=wf,
        project_id=project_uuid,
        action=ACTION_SUBMIT_PREFERENCES,
    )

    row = PreferencesService().submit_preference(
        db,
        workflow=wf,
        project_id=project_uuid,
        t=payload.t,
        participant_id=principal.participant_id,
        payload=payload.model_dump(),
    )

    return {
        "receipt_id": _receipt_id(),
        "workflow": payload.workflow,
        "projectId": payload.projectId,
        "t": payload.t,
        "bidId": str(row.id),
        "status": "stored_submitted" if row.state == "submitted" else "stored_draft",
        "signature_hash": row.signature_hash,
    }


@router.get(
    "/preferences/my",
    dependencies=[Depends(strict_workflow_scope)],
    response_model=MyPreferenceResponse,
)
async def get_my_preference(
    request: Request,
    t: int = Query(..., ge=0),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    if request.state.workflow != "slum":
        raise HTTPException(status_code=400, detail="Only slum workflow supported.")

    try:
        project_uuid = uuid.UUID(request.state.project_id)
    except Exception:
        raise HTTPException(
            status_code=400, detail="projectId must be UUID (Project.id)."
        )

    svc = PreferencesService()
    row = svc.get_my_preference(
        db,
        workflow="slum",
        project_id=project_uuid,
        t=t,
        participant_id=principal.participant_id,
    )
    if not row:
        raise HTTPException(
            status_code=404, detail="Preference not found for this round."
        )

    return {
        "workflow": "slum",
        "projectId": request.state.project_id,
        "t": t,
        "state": row.state,
        "submitted_at_iso": _iso(row.submitted_at),
        "locked_at_iso": _iso(row.locked_at),
        "payload": row.payload_json,
    }


@router.post(
    "/preferences/draft",
    dependencies=[Depends(strict_workflow_scope)],
    response_model=BidReceipt,
)
async def save_preference_draft(
    request: Request,
    payload: PreferenceBidPayload,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    # RBAC + policy (same as submit)
    try:
        require_action(principal, ACTION_SUBMIT_PREFERENCES)
        enforce_slum_dweller_role(principal)
        enforce_slum_workflow_only(request.state.workflow)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if payload.workflow.value != request.state.workflow:
        raise HTTPException(status_code=400, detail="Workflow mismatch.")
    if payload.projectId != request.state.project_id:
        raise HTTPException(status_code=400, detail="ProjectId mismatch.")

    try:
        project_uuid = uuid.UUID(request.state.project_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid projectId.")

    svc = PreferencesService()
    row = svc.core.save_preference_draft(
        db,
        workflow="slum",
        project_id=project_uuid,
        t=payload.t,
        participant_id=principal.participant_id,
        payload=payload.model_dump(),
    )

    return {
        "receipt_id": _receipt_id(),
        "workflow": payload.workflow,
        "projectId": payload.projectId,
        "t": payload.t,
        "bidId": str(row.id),
        "status": "stored_draft",
        "signature_hash": row.signature_hash,
    }
