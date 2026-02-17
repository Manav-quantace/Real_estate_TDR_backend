from __future__ import annotations

import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth_deps import get_current_principal
from app.services.government_charge_service import GovernmentChargeService

router = APIRouter(prefix="/government-charges")


@router.get("")
def get_charge(
    roundId: str,
    chargeType: str,
    db: Session = Depends(get_db),
):
    try:
        rid = uuid.UUID(roundId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid roundId")

    svc = GovernmentChargeService()
    row = svc.get(db, round_id=rid, charge_type=chargeType)
    return row


@router.get("/history")
def get_history(
    roundId: str,
    chargeType: str,
    db: Session = Depends(get_db),
):
    rid = uuid.UUID(roundId)
    svc = GovernmentChargeService()
    return svc.history(db, round_id=rid, charge_type=chargeType)


@router.post("")
def upsert_charge(
    body: dict,
    db: Session = Depends(get_db),
    principal=Depends(get_current_principal),
):
    svc = GovernmentChargeService()
    try:
        row = svc.upsert(
            db,
            round_id=uuid.UUID(body["roundId"]),
            charge_type=body["chargeType"],
            weights=body.get("weights", {}),
            inputs=body.get("inputs", {}),
            value_inr=body.get("valueInr"),
            actor_participant_id=principal.participant_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {"status": "ok", "charge": row}
