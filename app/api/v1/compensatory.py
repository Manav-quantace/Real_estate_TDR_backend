from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps_params import require_workflow_project_scope
from app.schemas.compensatory import CompensatoryEventResponse
from app.services.compensatory_service import CompensatoryService

router = APIRouter(prefix="/events")


def _iso(dt):
    return dt.isoformat() if dt else None


@router.get("/compensatory", response_model=CompensatoryEventResponse, dependencies=[Depends(require_workflow_project_scope)])
async def get_compensatory_event(
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

    svc = CompensatoryService()
    try:
        row = svc.compute_and_store_if_needed(db, workflow=workflow, project_id=project_uuid, t=t)
    except ValueError as e:
        msg = str(e)
        if "No default recorded" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=409, detail=msg)

    return {
        "workflow": workflow,
        "projectId": pid_raw,
        "t": t,
        "status": row.status,
        "computed_at_iso": _iso(row.computed_at),

        "original_winner_quote_bid_id": str(row.original_winner_quote_bid_id),
        "original_second_quote_bid_id": str(row.original_second_quote_bid_id),
        "original_bsecond_inr": str(row.original_bsecond_inr),

        "new_winner_quote_bid_id": str(row.new_winner_quote_bid_id) if row.new_winner_quote_bid_id else None,
        "new_second_quote_bid_id": str(row.new_second_quote_bid_id) if row.new_second_quote_bid_id else None,

        "bsecond_new_raw_inr": str(row.bsecond_new_raw_inr) if row.bsecond_new_raw_inr is not None else None,
        "bsecond_new_enforced_inr": str(row.bsecond_new_enforced_inr) if row.bsecond_new_enforced_inr is not None else None,

        "enforcement_action": row.enforcement_action,
        "notes": row.notes_json or {},
    }
