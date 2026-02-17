from __future__ import annotations

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.core.types import WorkflowType


class RoundWindowStatus(BaseModel):
    t: int = Field(..., ge=0)
    state: str
    is_open: bool
    is_locked: bool
    bidding_window_start_iso: Optional[str] = None
    bidding_window_end_iso: Optional[str] = None


class AggregateStats(BaseModel):
    count_total: int = 0

    # For quote bids (buyer side)
    quote_qbundle_min_inr: Optional[str] = None
    quote_qbundle_max_inr: Optional[str] = None

    # For ask bids (developer DCU asks)
    ask_total_min_inr: Optional[str] = None
    ask_total_max_inr: Optional[str] = None

    # For compensatory asks (if present)
    comp_ask_ppu_min_inr: Optional[str] = None
    comp_ask_ppu_max_inr: Optional[str] = None


class FeedbackRoundResponse(BaseModel):
    workflow: WorkflowType
    projectId: str
    t: int

    round: RoundWindowStatus

    # User-specific flags (safe booleans only)
    user_submitted_quote: bool = False
    user_submitted_ask: bool = False
    user_submitted_preferences: bool = False

    # Aggregates (no identities)
    aggregates: Dict[str, Any] = Field(default_factory=dict)

    # Adjustment window (structural)
    adjustment_allowed: bool
    adjustment_reason: Optional[str] = None
