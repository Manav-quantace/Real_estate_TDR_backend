# app/api/v1/rounds.py
from __future__ import annotations

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_principal
from app.core.deps_params import require_workflow_project_scope
from app.db.session import get_db

from app.models.project import Project
from app.models.round import Round

from app.schemas.rounds import (
    RoundOpenRequest,
    RoundCloseRequest,
    RoundLockRequest,
    RoundResponse,
)
from app.schemas.primitives import BidRound
from app.services.rounds_service import RoundService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/rounds")


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid ISO datetime: {s}")


def _authority_only(principal):
    if principal.role.value != "GOV_AUTHORITY":
        raise HTTPException(
            status_code=403,
            detail="Only GOV_AUTHORITY may manage rounds.",
        )


def _normalize_state(r: Round) -> str:
    """
    Map DB state → UI state
    """
    if r.is_locked:
        return "locked"
    if r.is_open:
        return "open"
    if r.state == "submitted":
        return "closed"
    return "new"


def _round_to_schema(r: Round) -> BidRound:
    return BidRound(
        id=str(r.id),
        t=r.t,
        state=_normalize_state(r),
        bidding_window_start=r.bidding_window_start.isoformat() if r.bidding_window_start else None,
        bidding_window_end=r.bidding_window_end.isoformat() if r.bidding_window_end else None,
        is_open=bool(r.is_open),
        is_locked=bool(r.is_locked),
    )


# ─────────────────────────────────────────────────────────────
# GET CURRENT ROUND
# ─────────────────────────────────────────────────────────────

@router.get(
    "/current",
    response_model=RoundResponse,
    dependencies=[Depends(require_workflow_project_scope)],
)
async def get_current_round(
    request: Request,
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    workflow = request.state.workflow
    project_id_raw = request.state.project_id

    try:
        project_uuid = uuid.UUID(project_id_raw)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID (Project.id).")

    project = (
        db.query(Project)
        .filter(Project.workflow == workflow, Project.id == project_uuid)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    svc = RoundService()
    rnd = svc.get_current_round(db, workflow, project_uuid)

    if not rnd:
        return RoundResponse(
            workflow=workflow,
            projectId=str(project_uuid),
            current=None,
    )

    return RoundResponse(
        workflow=workflow,
        projectId=str(project_uuid),
        current=_round_to_schema(rnd),
    )


# ─────────────────────────────────────────────────────────────
# OPEN ROUND
# ─────────────────────────────────────────────────────────────

@router.post("/open", response_model=RoundResponse)
async def open_round(
    req: RoundOpenRequest,
    request: Request,
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    _authority_only(principal)

    workflow = req.workflow.value
    project_uuid = uuid.UUID(req.projectId)

    project = (
        db.query(Project)
        .filter(Project.workflow == workflow, Project.id == project_uuid)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    svc = RoundService()
    try:
        rnd = svc.open_next_round(
            db,
            workflow=workflow,
            project_id=project_uuid,
            window_start=_parse_iso(req.bidding_window_start_iso),
            window_end=_parse_iso(req.bidding_window_end_iso),
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    AuditService().write(
        db,
        workflow=workflow,
        project_id=str(project_uuid),
        t=rnd.t,
        actor_participant_id=principal.participant_id,
        action="ROUND_OPENED",
        request_id=getattr(request.state, "request_id", None),
        details={"t": rnd.t},
    )

    return RoundResponse(
        workflow=workflow,
        projectId=str(project_uuid),
        current=_round_to_schema(rnd),
    )


# ─────────────────────────────────────────────────────────────
# CLOSE ROUND
# ─────────────────────────────────────────────────────────────

@router.post("/close", response_model=RoundResponse)
async def close_round(
    req: RoundCloseRequest,
    request: Request,
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    _authority_only(principal)

    workflow = req.workflow.value
    project_uuid = uuid.UUID(req.projectId)

    svc = RoundService()
    try:
        rnd = svc.close_round(
            db,
            workflow=workflow,
            project_id=project_uuid,
            t=req.t,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    AuditService().write(
        db,
        workflow=workflow,
        project_id=str(project_uuid),
        t=req.t,
        actor_participant_id=principal.participant_id,
        action="ROUND_CLOSED",
        request_id=getattr(request.state, "request_id", None),
        details={"t": req.t},
    )

    return RoundResponse(
        workflow=workflow,
        projectId=str(project_uuid),
        current=_round_to_schema(rnd),
    )


# ─────────────────────────────────────────────────────────────
# LOCK ROUND
# ─────────────────────────────────────────────────────────────

@router.post("/lock", response_model=RoundResponse)
async def lock_round(
    req: RoundLockRequest,
    request: Request,
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    _authority_only(principal)

    workflow = req.workflow.value
    project_uuid = uuid.UUID(req.projectId)

    svc = RoundService()
    try:
        rnd = svc.lock_round(
            db,
            workflow=workflow,
            project_id=project_uuid,
            t=req.t,
            actor_participant_id=principal.participant_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    AuditService().write(
        db,
        workflow=workflow,
        project_id=str(project_uuid),
        t=req.t,
        actor_participant_id=principal.participant_id,
        action="ROUND_LOCKED",
        request_id=getattr(request.state, "request_id", None),
        details={"t": req.t, "round_id": str(rnd.id)},
    )

    return RoundResponse(
        workflow=workflow,
        projectId=str(project_uuid),
        current=_round_to_schema(rnd),
    )


# ─────────────────────────────────────────────────────────────
# LIST ROUND HISTORY
# ─────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=list[BidRound],
    dependencies=[Depends(require_workflow_project_scope)],
)
async def list_rounds(
    request: Request,
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    workflow = request.state.workflow
    project_uuid = uuid.UUID(request.state.project_id)

    rounds = (
        db.query(Round)
        .filter(
            Round.workflow == workflow,
            Round.project_id == project_uuid,
        )
        .order_by(Round.t.asc())
        .all()
    )

    return [_round_to_schema(r) for r in rounds]
