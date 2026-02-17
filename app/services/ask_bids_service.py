# app/services/ask_bids_service.py
from __future__ import annotations

import uuid
from typing import Dict, Any
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.models.ask_bid import AskBid
from app.services.bids_service import BidService


def _to_dec(x):
    if x is None:
        return None
    try:
        return Decimal(str(x))
    except (InvalidOperation, TypeError):
        raise ValueError("Invalid numeric field.")


class AskBidsService:
    def __init__(self):
        self.core = BidService()

    def submit_ask_bid(
        self,
        db: Session,
        *,
        workflow: str,
        project_id: uuid.UUID,
        t: int,
        participant_id: str,
        payload: Dict[str, Any],
    ) -> AskBid:
        """
        Canonical ASK submission.

        RULE:
        - total_ask_inr is ALWAYS computed server-side
        - UI-provided value is ignored if inconsistent
        """

        # Core bid submission (state, locking, round checks)
        row = self.core.submit_ask(db, workflow, project_id, t, participant_id, payload)

        # Extract canonical numeric fields
        dcu_units = _to_dec(payload.get("dcu_units"))
        ask_price = _to_dec(payload.get("ask_price_per_unit_inr"))

        if dcu_units is None or ask_price is None:
            raise ValueError("dcu_units and ask_price_per_unit_inr are required.")

        if dcu_units <= 0 or ask_price <= 0:
            raise ValueError("DCU units and ask price must be positive.")

        # ✅ CANONICAL DERIVATION (THIS WAS MISSING)
        total_ask = (dcu_units * ask_price).quantize(Decimal("0.01"))

        # Optional compensatory fields (structural only)
        comp_units = _to_dec(payload.get("compensatory_dcu_units"))
        comp_price = _to_dec(payload.get("compensatory_ask_price_per_unit_inr"))
        delta_next = _to_dec(payload.get("delta_ask_next_round_inr"))

        # Mirror into indexed columns
        row.dcu_units = dcu_units
        row.ask_price_per_unit_inr = ask_price
        row.total_ask_inr = total_ask

        row.comp_dcu_units = comp_units
        row.comp_ask_price_per_unit_inr = comp_price
        row.delta_ask_next_round_inr = delta_next

        db.add(row)
        db.commit()
        db.refresh(row)
        return row
