from __future__ import annotations
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.core.types import WorkflowType


class CompensatoryEventResponse(BaseModel):
    workflow: WorkflowType
    projectId: str
    t: int = Field(..., ge=0)

    status: str
    computed_at_iso: str

    original_winner_quote_bid_id: str
    original_second_quote_bid_id: str
    original_bsecond_inr: str

    new_winner_quote_bid_id: Optional[str] = None
    new_second_quote_bid_id: Optional[str] = None

    bsecond_new_raw_inr: Optional[str] = None
    bsecond_new_enforced_inr: Optional[str] = None

    enforcement_action: str
    notes: Dict[str, Any] = Field(default_factory=dict)
