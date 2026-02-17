# app/api/v1/bids.py
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import uuid

from app.core.auth_deps import get_current_principal
from app.db.session import get_db
from app.models.ask_bid import AskBid
from app.policies.rbac import Principal

"""
LEGACY / READ-ONLY BIDS ROUTER

⚠️ IMPORTANT:
This router MUST NOT define any POST endpoints.

Canonical write endpoints live in:
- app/api/v1/bids_ask.py
- app/api/v1/bids_quote.py
- app/api/v1/preferences.py

This file exists ONLY for:
- read-only helpers
- backward compatibility
"""

router = APIRouter(prefix="/bids")


# ---------------------------------------------------------------------
# ✅ READ-ONLY: GET MY ASK (Developer)
# ---------------------------------------------------------------------

@router.get("/ask/my")
def get_my_asks(
    workflow: str = Query(...),
    projectId: uuid.UUID = Query(...),
    t: int = Query(...),
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
):
    if principal.role.value != "DEVELOPER":
        raise HTTPException(status_code=403, detail="Only developers can view asks")

    rows = (
        db.query(AskBid)
        .filter(
            AskBid.workflow == workflow,
            AskBid.project_id == projectId,
            AskBid.t == t,
            AskBid.participant_id == principal.participant_id,
        )
        .all()
    )

    if not rows:
        return None

    r = rows[0]
    return {
        "dcu_units": float(r.dcu_units) if r.dcu_units is not None else None,
        "ask_price_per_unit_inr": float(r.ask_price_per_unit_inr)
        if r.ask_price_per_unit_inr is not None
        else None,
        "state": r.state,
    }
