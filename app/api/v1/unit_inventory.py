# app/api/v1/unit_inventory.py
from __future__ import annotations

import uuid
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.auth_deps import get_current_principal
from app.policies.rbac import Principal

from app.services.unit_inventory_service import UnitInventoryService
from app.models.round import Round

router = APIRouter(prefix="/unit-inventory")


def _authority_only(principal: Principal):
    if principal.role.value != "GOV_AUTHORITY":
        raise HTTPException(
            status_code=403, detail="Only GOV_AUTHORITY may manage inventory."
        )


def _to_resp(inv):
    return {
        "roundId": str(inv.round_id),
        "lu": str(inv.lu) if inv.lu is not None else None,
        "tdru": str(inv.tdru) if inv.tdru is not None else None,
        "pru": str(inv.pru) if inv.pru is not None else None,
        "dcu": str(inv.dcu) if inv.dcu is not None else None,
    }


@router.get("")
def get_inventory(
    roundId: str = Query(...),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    try:
        rid = uuid.UUID(roundId)
    except Exception:
        raise HTTPException(status_code=400, detail="roundId must be UUID.")

    inv = UnitInventoryService().get_for_round(db, round_id=rid)
    return _to_resp(inv) if inv else None


@router.post("")
def upsert_inventory(
    body: dict,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    _authority_only(principal)

    if "roundId" not in body:
        raise HTTPException(status_code=400, detail="roundId required.")

    try:
        rid = uuid.UUID(body["roundId"])
    except Exception:
        raise HTTPException(status_code=400, detail="roundId must be UUID.")

    try:
        inv = UnitInventoryService().upsert_for_round(
            db,
            round_id=rid,
            lu=Decimal(str(body["lu"])) if body.get("lu") is not None else None,
            tdru=Decimal(str(body["tdru"])) if body.get("tdru") is not None else None,
            pru=Decimal(str(body["pru"])) if body.get("pru") is not None else None,
            dcu=Decimal(str(body["dcu"])) if body.get("dcu") is not None else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return _to_resp(inv)
