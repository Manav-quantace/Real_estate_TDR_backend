from __future__ import annotations
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.core.types import WorkflowType


class SettlementResultResponse(BaseModel):
    workflow: WorkflowType
    projectId: str
    t: int = Field(..., ge=0)

    status: str
    settled: bool

    # Winner and references (may be redacted based on role)
    winner_quote_bid_id: Optional[str] = None
    winning_ask_bid_id: Optional[str] = None
    second_price_quote_bid_id: Optional[str] = None

    max_quote_inr: Optional[str] = None
    second_price_inr: Optional[str] = None
    min_ask_total_inr: Optional[str] = None

    computed_at_iso: str

    # Receipt is role-filtered; never contains other participants’ raw bid payloads
    receipt: Dict[str, Any] = Field(default_factory=dict)