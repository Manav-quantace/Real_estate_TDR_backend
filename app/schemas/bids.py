from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.core.types import WorkflowType
from app.schemas.primitives import MoneyINR, NonNegDec4, NonNegInt, ScopedRef


class QuoteBidPayload(ScopedRef):
    """
    Buyer-side quote payload (structural).

    Qbundle is allowed as a single bundle quote.
    If API expects decomposition (QTDR/QLU/QPRU), store them as optional fields.
    No computations performed.
    """

    t: NonNegInt = Field(..., description="Round index t")
    qbundle_inr: MoneyINR = Field(..., description="Qbundle in INR (structural)")

    # optional decomposition if required by API contract later
    qlu_inr: Optional[MoneyINR] = Field(default=None)
    qtdr_inr: Optional[MoneyINR] = Field(default=None)
    qpru_inr: Optional[MoneyINR] = Field(default=None)

    # optional: API may provide Qnet; backend stores/returns it later (not computed here)
    qnet_inr: Optional[MoneyINR] = Field(
        default=None, description="Qnet (if provided by API)"
    )

    bid_validity_iso: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None, max_length=2000)


class AskBidPayload(ScopedRef):
    """
    Developer-side ASK payload.
    STRICT: DCU-only for developer-side roles (enforced in Part 3 policies AND here structurally).

    This schema itself forbids LU/TDRU/PRU fields by not defining them.
    Additionally, we validate that DCU fields exist and are non-negative.
    """

    t: NonNegInt = Field(..., description="Round index t")

    dcu_units: NonNegDec4 = Field(..., description="DCU units offered (structural)")
    ask_price_per_unit_inr: MoneyINR = Field(
        ..., description="Ask price per DCU unit (INR)"
    )
    total_ask_inr: Optional[MoneyINR] = Field(
        default=None,
        description="Optional total ask (if API provides; not computed here)",
    )

    # Compensatory DCU fields (structural only)
    compensatory_dcu_units: Optional[NonNegDec4] = Field(default=None)
    compensatory_ask_price_per_unit_inr: Optional[MoneyINR] = Field(default=None)

    bid_validity_iso: Optional[str] = Field(default=None)
    notes: Optional[str] = Field(default=None, max_length=2000)

    # Iteration adjustment storage (structural)
    delta_ask_next_round_inr: Optional[Decimal] = Field(
        default=None, description="ΔAsk(t+1) (structural)"
    )

    @model_validator(mode="after")
    def _validate_dcu_only(self):
        # DCU units required (already)
        if self.dcu_units is None:
            raise ValueError("dcu_units is required for AskBidPayload (DCU-only).")
        return self


class TripartitePreferencePayload(ScopedRef):
    """
    Slum dweller preferences (slum workflow only).
    """

    t: NonNegInt = Field(..., description="Round index t")
    rehab_option: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="desired rehabilitation option (structural)",
    )
    household_details: dict = Field(
        default_factory=dict,
        description="workflow-required household fields (structural)",
    )
    consent: dict = Field(
        default_factory=dict, description="consent toggles (structural)"
    )
    notes: Optional[str] = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _slum_only(self):
        if self.workflow != WorkflowType.slum:
            raise ValueError(
                "TripartitePreferencePayload is only valid for workflow=slum."
            )
        return self
