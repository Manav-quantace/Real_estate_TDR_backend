# app/api/v1/settlement.py
from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.session import get_db
from app.core.deps_params import require_workflow_project_scope
from app.core.auth_deps import get_current_principal
from app.core.redaction import mask_uuid
from app.schemas.settlement import SettlementResultResponse
from app.services.settlement_service import SettlementService
from app.models.quote_bid import QuoteBid
from app.models.ask_bid import AskBid

router = APIRouter(prefix="/settlement")


def _iso(dt):
    return dt.isoformat() if dt else None


def _is_authority(principal) -> bool:
    return principal.role.value in {"GOV_AUTHORITY", "AUDITOR"}


def _participant_owns_quote(db: Session, bid_id: uuid.UUID, participant_id: str) -> bool:
    row = db.execute(select(QuoteBid.participant_id).where(QuoteBid.id == bid_id)).scalar_one_or_none()
    return bool(row == participant_id)


def _participant_owns_ask(db: Session, bid_id: uuid.UUID, participant_id: str) -> bool:
    row = db.execute(select(AskBid.participant_id).where(AskBid.id == bid_id)).scalar_one_or_none()
    return bool(row == participant_id)


@router.get("/result", response_model=SettlementResultResponse, dependencies=[Depends(require_workflow_project_scope)])
async def get_settlement_result(
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

    svc = SettlementService()
    try:
        row = svc.compute_and_store_if_needed(db, workflow=workflow, project_id=project_uuid, t=t)
    except ValueError as e:
        msg = str(e)
        if "only after round lock" in msg:
            raise HTTPException(status_code=409, detail=msg)
        if "Round not found" in msg:
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

    # Role-based visibility
    full = _is_authority(principal)

    winner_id = row.winner_quote_bid_id
    ask_id = row.winning_ask_bid_id
    second_id = row.second_price_quote_bid_id

    # Decide what IDs to reveal
    if full:
        out_winner = str(winner_id) if winner_id else None
        out_ask = str(ask_id) if ask_id else None
        out_second = str(second_id) if second_id else None
        receipt = row.receipt_json or {}
    else:
        # non-authority: reveal only if caller owns that bid; otherwise redact
        out_winner = None
        out_ask = None
        out_second = None

        if winner_id and _participant_owns_quote(db, winner_id, principal.participant_id):
            out_winner = str(winner_id)
        elif winner_id:
            out_winner = mask_uuid(winner_id)

        if ask_id and _participant_owns_ask(db, ask_id, principal.participant_id):
            out_ask = str(ask_id)
        elif ask_id:
            out_ask = mask_uuid(ask_id)

        # second-price bid belongs to another buyer typically -> redact
        if second_id and _participant_owns_quote(db, second_id, principal.participant_id):
            out_second = str(second_id)
        elif second_id:
            out_second = mask_uuid(second_id)

        # receipt filtered: keep rule + hashes, remove raw IDs that aren't theirs
        receipt = row.receipt_json or {}
        # Remove detailed references for non-authority except status
        receipt = {
            "status": receipt.get("status"),
            "vickrey_rule": receipt.get("vickrey_rule"),
            "second_price_reference": receipt.get("second_price_reference"),
            "inputs": {
                # show only hash values (safe) + your own if present
                "winner_quote_signature_hash": receipt.get("inputs", {}).get("winner_quote_signature_hash"),
                "winning_ask_signature_hash": receipt.get("inputs", {}).get("winning_ask_signature_hash"),
                "second_quote_signature_hash": receipt.get("inputs", {}).get("second_quote_signature_hash"),
            },
        }

    settled_bool = bool(row.settled == "true" if isinstance(row.settled, str) else row.settled)

    return {
        "workflow": workflow,
        "projectId": pid_raw,
        "t": t,
        "status": row.status,
        "settled": settled_bool,
        "winner_quote_bid_id": out_winner,
        "winning_ask_bid_id": out_ask,
        "second_price_quote_bid_id": out_second,
        "max_quote_inr": str(row.max_quote_inr) if row.max_quote_inr is not None else None,
        "second_price_inr": str(row.second_price_inr) if row.second_price_inr is not None else None,
        "min_ask_total_inr": str(row.min_ask_total_inr) if row.min_ask_total_inr is not None else None,
        "computed_at_iso": _iso(row.computed_at),
        "receipt": receipt,
    }
