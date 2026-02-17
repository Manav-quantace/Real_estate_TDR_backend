from __future__ import annotations

from typing import Optional, List

from pydantic import BaseModel, Field

from app.schemas.primitives import ScopedRef, BidRound, MoneyINR


class MatchingResult(ScopedRef):
    """
    Matching output (API-driven).
    No computations here: store references and summary fields.
    """

    t: int = Field(..., ge=0)
    round: BidRound
    status: str = Field(..., description="MATCHED / NO_MATCH / PARTIAL (structural)")
    summary: dict = Field(
        default_factory=dict, description="workflow-specific matching summary"
    )
    matched_entities: list = Field(
        default_factory=list,
        description="IDs of matched participants/entities as returned by API",
    )
    trace: dict = Field(
        default_factory=dict, description="hash refs / provenance ids (structural)"
    )


class SettlementReceipt(BaseModel):
    receipt_id: str
    currency: str = "INR"
    amount_inr: MoneyINR
    created_at_iso: Optional[str] = None
    references: dict = Field(default_factory=dict, description="bid ids, hashes, etc")


class SettlementResult(ScopedRef):
    """
    Vickrey settlement output (API-driven).
    Winners + second-price payments are provided; backend stores and returns.
    """

    t: int = Field(..., ge=0)
    round: BidRound
    status: str = Field(..., description="READY / PENDING / FAILED (structural)")
    winners: list = Field(
        default_factory=list, description="winner records returned by API"
    )
    second_price_payments: list = Field(
        default_factory=list, description="second-price payment records (structural)"
    )
    receipts: List[SettlementReceipt] = Field(default_factory=list)
    audit_link: Optional[str] = None
    trace: dict = Field(default_factory=dict)
