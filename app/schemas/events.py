from __future__ import annotations
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.core.types import WorkflowType


class DefaultDeclareRequest(BaseModel):
    workflow: WorkflowType
    projectId: str
    t: int = Field(..., ge=0)
    reason: Optional[str] = None


class PenaltyEventResponse(BaseModel):
    workflow: WorkflowType
    projectId: str
    t: int

    winner_quote_bid_id: str
    second_price_quote_bid_id: str

    bmax_inr: str
    bsecond_inr: str
    penalty_inr: str

    enforcement_status: str
    computed_at_iso: str

    notes: Dict[str, Any] = Field(default_factory=dict)