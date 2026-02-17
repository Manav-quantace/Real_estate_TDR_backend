from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from app.core.auth_deps import get_current_principal
from app.db.session import get_db
from app.core.deps_params import require_workflow_project_scope
from app.schemas.feedback import FeedbackRoundResponse, RoundWindowStatus
from app.services.feedback_service import FeedbackService

router = APIRouter(prefix="/feedback")


def _iso(dt):
    return dt.isoformat() if dt else None


@router.get("/round", response_model=FeedbackRoundResponse, dependencies=[Depends(require_workflow_project_scope)])
async def feedback_round(
    request: Request,
    t: int = Query(..., ge=0),
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    workflow = request.state.workflow
    pid_raw = request.state.project_id

    try:
        project_uuid = uuid.UUID(pid_raw)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID (Project.id).")

    svc = FeedbackService()
    rnd = svc.get_round(db, workflow, project_uuid, t)
    if not rnd:
        raise HTTPException(status_code=404, detail="Round not found for workflow/projectId/t.")

    flags = svc.user_submission_flags(
        db, workflow=workflow, project_id=project_uuid, t=t, participant_id=principal.participant_id
    )
    aggregates = svc.aggregate_stats(db, workflow=workflow, project_id=project_uuid, t=t)

    # Adjustment window: allowed only if round open and not locked
    if rnd.is_locked:
        adjustment_allowed = False
        reason = "round_locked"
    elif not rnd.is_open:
        adjustment_allowed = False
        reason = "round_closed"
    else:
        adjustment_allowed = True
        reason = None

    response = {
        "workflow": workflow,
        "projectId": pid_raw,
        "t": t,
        "round": {
            "t": rnd.t,
            "state": rnd.state,
            "is_open": bool(rnd.is_open),
            "is_locked": bool(rnd.is_locked),
            "bidding_window_start_iso": _iso(rnd.bidding_window_start),
            "bidding_window_end_iso": _iso(rnd.bidding_window_end),
        },
        **flags,
        "aggregates": aggregates,
        "adjustment_allowed": adjustment_allowed,
        "adjustment_reason": reason,
    }

    # Anti-leak: forbid any of these in the response (hard stop)
    forbidden = {
        "participant_id", "participantId", "payload_json", "payload", "bidId",
        "orderbook", "asks", "bids", "allBids", "quoteBook", "askBook", "marketDepth",
    }
    if any(k in response for k in forbidden):
        raise RuntimeError("Privacy violation: forbidden key present in feedback response.")
    return response

