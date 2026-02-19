# app/api/v1/bids_ask.py
from __future__ import annotations

import uuid
import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from app.core.deps import strict_workflow_scope
from app.core.auth_deps import get_current_principal
from app.db.session import get_db

from app.models.ask_bid import AskBid
from app.models.bid_enums import BidState

from app.policies.rbac import (
    ACTION_SUBMIT_ASK,
    require_action,
    Principal,
)
from app.policies.bid_policies import enforce_developer_dcu_only

from app.schemas.bids import AskBidPayload
from app.schemas.bid_receipts import BidReceipt

from app.services.ask_bids_service import AskBidsService

from app.policies.clearland_phase_policy import enforce_phase_allows_action
from app.policies.clearland_membership_policy import enforce_active_clearland_membership

router = APIRouter(prefix="/bids")


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------


def _receipt_id() -> str:
    return "RCP-" + secrets.token_hex(8).upper()


def _anti_leak_assert_no_orderbook(response_obj: dict) -> None:
    """
    Safety guard: never accidentally return orderbook-like structures.
    """
    forbidden_keys = {
        "orderbook",
        "asks",
        "bids",
        "allBids",
        "marketDepth",
        "quoteBook",
        "askBook",
    }
    if any(k in response_obj for k in forbidden_keys):
        raise RuntimeError("Anti-leak: attempted to return orderbook-like keys.")


def _reject_non_dcu_fields(payload_dict: dict) -> None:
    """
    Extra hardening: developers may NOT submit LU/TDRU/PRU-like fields.
    """
    forbidden = {
        "lu",
        "LU",
        "tdru",
        "TDRU",
        "pru",
        "PRU",
        "qtdr_inr",
        "qlu_inr",
        "qpru_inr",
    }
    if any(k in payload_dict for k in forbidden):
        raise HTTPException(
            status_code=400, detail="Developers may only submit DCU-related ask fields."
        )


# ---------------------------------------------------------------------
# POST /v1/bids/ask  (Developer submit)
# ---------------------------------------------------------------------


# app/api/v1/bids_ask.py
@router.post(
    "/ask",
    dependencies=[Depends(strict_workflow_scope)],
    response_model=BidReceipt,
)
async def post_ask_bid(
    request: Request,
    payload: AskBidPayload,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    wf = request.state.workflow
    pid_raw = request.state.project_id

    try:
        project_uuid = uuid.UUID(pid_raw)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    try:
        require_action(principal, ACTION_SUBMIT_ASK)

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
            action=ACTION_SUBMIT_ASK,
        )

        enforce_developer_dcu_only(principal)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if payload.workflow.value != wf:
        raise HTTPException(status_code=400, detail="Payload workflow mismatch.")
    if payload.projectId != pid_raw:
        raise HTTPException(status_code=400, detail="Payload projectId mismatch.")

    _reject_non_dcu_fields(payload.model_dump())

    row = AskBidsService().submit_ask_bid(
        db,
        workflow=wf,
        project_id=project_uuid,
        t=payload.t,
        participant_id=principal.participant_id,
        payload=payload.model_dump(),
    )

    response = {
        "receipt_id": _receipt_id(),
        "workflow": payload.workflow,
        "projectId": payload.projectId,
        "t": payload.t,
        "bidId": str(row.id),
        "status": (
            "stored_submitted"
            if row.state == BidState.submitted.value
            else "stored_draft"
        ),
        "signature_hash": row.signature_hash,
    }

    _anti_leak_assert_no_orderbook(response)
    return response


# ---------------------------------------------------------------------
# GET /v1/bids/ask  (Authority view)
# ---------------------------------------------------------------------


@router.get(
    "/ask",
    dependencies=[Depends(strict_workflow_scope)],
)
async def list_ask_bids_for_authority(
    request: Request,
    t: int = Query(..., ge=0),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    Authority-only view of ALL ask bids for a round.
    Sanitized, no payload_json.
    """

    # Only authority may view all bids
    if principal.role.value != "GOV_AUTHORITY":
        raise HTTPException(status_code=403, detail="Not authorized to view bids.")

    wf = request.state.workflow
    pid_raw = request.state.project_id

    try:
        project_uuid = uuid.UUID(pid_raw)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    rows: List[AskBid] = (
        db.query(AskBid)
        .filter(
            AskBid.workflow == wf,
            AskBid.project_id == project_uuid,
            AskBid.t == t,
        )
        .order_by(AskBid.ask_price_per_unit_inr.asc().nullslast())
        .all() 
    )

    response = {
        "workflow": wf,
        "projectId": pid_raw,
        "t": t,
        "count": len(rows),
        "bids": [
            {
                "participant_id": r.participant_id,
                "dcu_units": str(r.dcu_units) if r.dcu_units is not None else None,
                "ask_price_per_unit_inr": (
                    str(r.ask_price_per_unit_inr)
                    if r.ask_price_per_unit_inr is not None
                    else None
                ),
                "total_ask_inr": (
                    str(r.total_ask_inr) if r.total_ask_inr is not None else None
                ),
                "state": r.state,
                "submitted_at_iso": (
                    r.submitted_at.isoformat() if r.submitted_at else None
                ),
                "locked_at_iso": r.locked_at.isoformat() if r.locked_at else None,
            }
            for r in rows
        ],
    }

    _anti_leak_assert_no_orderbook(response)
    return response
