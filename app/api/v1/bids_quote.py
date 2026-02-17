# app/api/v1/bids_quote.py
from __future__ import annotations

import uuid
import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session

from app.core.deps import strict_workflow_scope
from app.core.auth_deps import get_current_principal
from app.db.session import get_db

from app.models.quote_bid import QuoteBid
from app.models.bid_enums import BidState

from app.policies.rbac import (
    ACTION_SUBMIT_QUOTE,
    require_action,
    Principal,
)
from app.policies.bid_policies import enforce_quote_payload_role

from app.schemas.bids import QuoteBidPayload
from app.schemas.bid_receipts import BidReceipt

from app.services.quote_bids_service import QuoteBidsService
from app.policies.clearland_phase_policy import enforce_phase_allows_action
from app.policies.clearland_membership_policy import enforce_active_clearland_membership


router = APIRouter(prefix="/bids")


# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------


def _receipt_id() -> str:
    return "RCP-" + secrets.token_hex(8).upper()


def _anti_leak_assert_no_orderbook(response_obj: dict) -> None:
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


# ---------------------------------------------------------------------
# POST /v1/bids/quote  (Participant submit)
# ---------------------------------------------------------------------


@router.post(
    "/quote",
    dependencies=[Depends(strict_workflow_scope)],
    response_model=BidReceipt,
)
async def post_quote_bid(
    request: Request,
    payload: QuoteBidPayload,
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
        require_action(principal, ACTION_SUBMIT_QUOTE)

        # 🔐 membership guard (clearland only, authority bypassed upstream)
        enforce_active_clearland_membership(
            db=db,
            workflow=wf,
            project_id=project_uuid,
            participant_id=principal.participant_id,
        )

        # 🔐 phase guard (clearland only)
        enforce_phase_allows_action(
            db=db,
            workflow=wf,
            project_id=project_uuid,
            action=ACTION_SUBMIT_QUOTE,
        )

        enforce_quote_payload_role(principal)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if payload.workflow.value != wf:
        raise HTTPException(status_code=400, detail="Payload workflow mismatch.")
    if payload.projectId != pid_raw:
        raise HTTPException(status_code=400, detail="Payload projectId mismatch.")

    row = QuoteBidsService().submit_quote_bid(
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
# GET /v1/bids/quote  (Authority view)
# ---------------------------------------------------------------------


@router.get(
    "/quote",
    dependencies=[Depends(strict_workflow_scope)],
)
async def list_quote_bids_for_authority(
    request: Request,
    t: int = Query(..., ge=0),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    """
    Authority-only view of ALL quote bids for a round.
    """

    if principal.role.value != "GOV_AUTHORITY":
        raise HTTPException(status_code=403, detail="Not authorized.")

    wf = request.state.workflow
    pid_raw = request.state.project_id

    try:
        project_uuid = uuid.UUID(pid_raw)
    except Exception:
        raise HTTPException(status_code=400, detail="projectId must be UUID.")

    rows: List[QuoteBid] = (
        db.query(QuoteBid)
        .filter(
            QuoteBid.workflow == wf,
            QuoteBid.project_id == project_uuid,
            QuoteBid.t == t,
        )
        .order_by(QuoteBid.created_at.asc())
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
                "state": r.state,
                "submitted_at_iso": (
                    r.submitted_at.isoformat() if r.submitted_at else None
                ),
                "locked_at_iso": r.locked_at.isoformat() if r.locked_at else None,
                "payload": r.payload_json,
            }
            for r in rows
        ],
    }

    _anti_leak_assert_no_orderbook(response)
    return response


@router.get(
    "/my",
    dependencies=[Depends(strict_workflow_scope)],
)
def get_my_quote_bids(
    request: Request,
    t: int = Query(..., ge=0),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    workflow = request.state.workflow
    project_id = uuid.UUID(request.state.project_id)

    rows = (
        db.query(QuoteBid)
        .filter(
            QuoteBid.workflow == workflow,
            QuoteBid.project_id == project_id,
            QuoteBid.t == t,
            QuoteBid.participant_id == principal.participant_id,
        )
        .order_by(QuoteBid.created_at.desc())
        .all()
    )

    return [
        {
            "id": str(r.id),
            "state": r.state,
            "payload": r.payload_json,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
            "locked_at": r.locked_at.isoformat() if r.locked_at else None,
        }
        for r in rows
    ]
