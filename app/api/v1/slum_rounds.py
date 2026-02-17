#app/api/v1/slum_rounds.py
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth_deps import get_current_principal
from app.policies.rbac import Principal

from app.services.slum_state_machine import SlumStateMachine

router = APIRouter(prefix="/slum")


def _require_authority(principal: Principal):
    if principal.role.value != "GOV_AUTHORITY":
        raise HTTPException(
            status_code=403, detail="Only authority can manage slum rounds."
        )


@router.post("/rounds/open")
def open_slum_round(
    projectId: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    Book rule:
    - Only authority
    - Only if tripartite portals exist
    """
    _require_authority(principal)

    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    sm = SlumStateMachine()
    try:
        rnd = sm.open_round_if_allowed(db, project_id=pid)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "round_opened",
        "workflow": "slum",
        "projectId": projectId,
        "t": rnd.t,
        "state": rnd.state,
        "is_open": rnd.is_open,
    }


@router.post("/rounds/close")
def close_slum_round(
    projectId: str = Query(..., min_length=1),
    t: int = Query(..., ge=0),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    _require_authority(principal)

    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    sm = SlumStateMachine()
    try:
        rnd = sm.close_round(db, project_id=pid, t=t)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "round_closed",
        "workflow": "slum",
        "projectId": projectId,
        "t": rnd.t,
        "state": rnd.state,
        "is_open": rnd.is_open,
        "is_locked": rnd.is_locked,
    }


@router.post("/rounds/lock")
def lock_slum_round(
    projectId: str = Query(..., min_length=1),
    t: int = Query(..., ge=0),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    _require_authority(principal)

    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    sm = SlumStateMachine()
    try:
        rnd = sm.lock_round(
            db,
            project_id=pid,
            t=t,
            actor_participant_id=principal.participant_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "round_locked",
        "workflow": "slum",
        "projectId": projectId,
        "t": rnd.t,
        "state": rnd.state,
        "is_open": rnd.is_open,
        "is_locked": rnd.is_locked,
    }


@router.post("/settlement/run")
def run_slum_settlement(
    projectId: str = Query(..., min_length=1),
    t: int = Query(..., ge=0),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    Book rule:
    - Only authority
    - Only after:
        • tripartite portals
        • round locked
    """
    _require_authority(principal)

    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    sm = SlumStateMachine()
    try:
        result = sm.run_settlement(db, project_id=pid, t=t)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "settlement_computed",
        "workflow": "slum",
        "projectId": projectId,
        "t": t,
        "settled": result.settled,
        "settlement_id": str(result.id),
    }


@router.get("/status")
def get_slum_status(
    projectId: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    Introspection endpoint for UI / admin.
    """
    try:
        pid = uuid.UUID(projectId)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    sm = SlumStateMachine()
    try:
        status = sm.get_slum_status(db, project_id=pid)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return status
