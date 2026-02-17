# app/api/v1/bids_my.py
from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, Request, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.round import Round
from app.models.ask_bid import AskBid
from app.models.quote_bid import QuoteBid
from app.models.preference_bid import PreferenceBid
from app.core.auth_deps import get_current_principal
from app.policies.rbac import Principal
from app.core.deps import strict_workflow_scope

router = APIRouter(prefix="/bids")


def _normalize_round(r: Round) -> dict:
    if not r:
        return None
    state = "new"
    if r.is_locked:
        state = "locked"
    elif r.is_open:
        state = "open"
    elif r.state == "submitted":
        state = "closed"
    return {
        "t": r.t,
        "state": state,
        "is_open": bool(r.is_open),
        "is_locked": bool(r.is_locked),
        "bidding_window_start": (
            r.bidding_window_start.isoformat() if r.bidding_window_start else None
        ),
        "bidding_window_end": (
            r.bidding_window_end.isoformat() if r.bidding_window_end else None
        ),
    }


@router.get(
    "/my-current",
    dependencies=[Depends(strict_workflow_scope)],
)
def get_my_bid_for_current_round(
    request: Request,
    portalType: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    Return the current round summary and, if present, the caller's bid for that round.
    - Respects workflow/project scope in request.state when available.
    - Also accepts workflow/projectId as query fallback (helps proxies).
    """

    # Resolve workflow/project
    wf = getattr(request.state, "workflow", None) or request.query_params.get(
        "workflow"
    )
    pid_raw = getattr(request.state, "project_id", None) or request.query_params.get(
        "projectId"
    )

    if not wf or not pid_raw:
        raise HTTPException(status_code=400, detail="workflow and projectId required")

    try:
        project_uuid = uuid.UUID(pid_raw)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID")

    # Current round (most recent t)
    rnd = (
        db.query(Round)
        .filter(Round.workflow == wf, Round.project_id == project_uuid)
        .order_by(Round.t.desc())
        .first()
    )

    round_payload = _normalize_round(rnd)

    # If no round at all, return round: null and bid: null
    if not rnd:
        return {"workflow": wf, "projectId": pid_raw, "round": None, "bid": None}

    t = rnd.t
    participant_id = principal.participant_id

    # Choose table by workflow/portalType
    row = None
    # SLUM specifics
    if wf == "slum":
        if portalType == "SLUM_DWELLER":
            row = (
                db.query(PreferenceBid)
                .filter_by(
                    workflow=wf,
                    project_id=project_uuid,
                    t=t,
                    participant_id=participant_id,
                )
                .order_by(PreferenceBid.created_at.desc())
                .first()
            )
        elif portalType == "SLUM_LAND_DEVELOPER":
            row = (
                db.query(AskBid)
                .filter_by(
                    workflow=wf,
                    project_id=project_uuid,
                    t=t,
                    participant_id=participant_id,
                )
                .order_by(AskBid.created_at.desc())
                .first()
            )
        elif portalType == "AFFORDABLE_HOUSING_DEV":
            row = (
                db.query(QuoteBid)
                .filter_by(
                    workflow=wf,
                    project_id=project_uuid,
                    t=t,
                    participant_id=participant_id,
                )
                .order_by(QuoteBid.created_at.desc())
                .first()
            )
        else:
            # Unknown portal for slum — safe fallback
            row = None

    else:
        # Non-slum workflows: be conservative.
        # Try to find any QuoteBid for this participant (saleable & others typically use quote).
        row = (
            db.query(QuoteBid)
            .filter_by(
                workflow=wf, project_id=project_uuid, t=t, participant_id=participant_id
            )
            .order_by(QuoteBid.created_at.desc())
            .first()
        )

    if not row:
        return {
            "workflow": wf,
            "projectId": pid_raw,
            "round": round_payload,
            "bid": None,
        }

    # Build bid payload (sanitized)
    bid_payload = {
        "id": str(row.id),
        "state": row.state,
        "submitted_at_iso": (
            row.submitted_at.isoformat() if getattr(row, "submitted_at", None) else None
        ),
        "locked_at_iso": (
            row.locked_at.isoformat() if getattr(row, "locked_at", None) else None
        ),
        # include common indexed columns if present
        "dcu_units": (
            str(getattr(row, "dcu_units", None))
            if getattr(row, "dcu_units", None) is not None
            else None
        ),
        "ask_price_per_unit_inr": (
            str(getattr(row, "ask_price_per_unit_inr", None))
            if getattr(row, "ask_price_per_unit_inr", None) is not None
            else None
        ),
        "total_ask_inr": (
            str(getattr(row, "total_ask_inr", None))
            if getattr(row, "total_ask_inr", None) is not None
            else None
        ),
        "payload": getattr(row, "payload_json", None),
        "signature_hash": getattr(row, "signature_hash", None),
    }

    return {
        "workflow": wf,
        "projectId": pid_raw,
        "round": round_payload,
        "bid": bid_payload,
    }
