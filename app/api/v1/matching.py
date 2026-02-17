#app/api/v1/matching.py
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps_params import require_workflow_project_scope
from app.schemas.matching import MatchingResultResponse
from app.services.matching_service import MatchingService

router = APIRouter(prefix="/matching")


def _iso(dt):
    return dt.isoformat() if dt else None


@router.post(
    "/run",
    dependencies=[Depends(require_workflow_project_scope)],
)
async def run_matching(
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

    match_svc = MatchingService()
    try:
        match = match_svc.compute_and_store_if_needed(
            db,
            workflow=workflow,
            project_id=project_uuid,
            t=t,
        )
    except ValueError as e:
        msg = str(e)
        if "only after round lock" in msg:
            raise HTTPException(status_code=409, detail=msg)
        if "Round not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    return {
        "workflow": workflow,
        "projectId": pid_raw,
        "t": t,
        "status": match.status,
        "matched": bool(match.matched),
        "selected_ask_bid_id": str(match.selected_ask_bid_id) if match.selected_ask_bid_id else None,
        "selected_quote_bid_id": str(match.selected_quote_bid_id) if match.selected_quote_bid_id else None,
        "min_ask_total_inr": str(match.min_ask_total_inr) if match.min_ask_total_inr else None,
        "max_quote_inr": str(match.max_quote_inr) if match.max_quote_inr else None,
        "computed_at_iso": _iso(match.computed_at),
        "notes": match.notes_json or {},
    }


@router.get(
    "/result",
    response_model=MatchingResultResponse,
    dependencies=[Depends(require_workflow_project_scope)],
)
async def get_matching_result(
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

    match_svc = MatchingService()
    try:
        match = match_svc.compute_and_store_if_needed(
            db,
            workflow=workflow,
            project_id=project_uuid,
            t=t,
        )
    except ValueError as e:
        msg = str(e)
        if "only after round lock" in msg:
            raise HTTPException(status_code=409, detail=msg)
        if "Round not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    return {
        "workflow": workflow,
        "projectId": pid_raw,
        "t": t,
        "status": match.status,
        "matched": bool(match.matched),
        "selected_ask_bid_id": str(match.selected_ask_bid_id) if match.selected_ask_bid_id else None,
        "selected_quote_bid_id": str(match.selected_quote_bid_id) if match.selected_quote_bid_id else None,
        "min_ask_total_inr": str(match.min_ask_total_inr) if match.min_ask_total_inr else None,
        "max_quote_inr": str(match.max_quote_inr) if match.max_quote_inr else None,
        "computed_at_iso": _iso(match.computed_at),
        "notes": match.notes_json or {},
    }
