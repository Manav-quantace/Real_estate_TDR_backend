from __future__ import annotations
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from app.core.types import WorkflowType


class DeveloperDefaultDeclareRequest(BaseModel):
    workflow: WorkflowType
    projectId: str
    t: int = Field(..., ge=0)
    reason: Optional[str] = None


class DeveloperCompensatoryEventResponse(BaseModel):
    workflow: WorkflowType
    projectId: str
    t: int

    status: str
    computed_at_iso: str

    original_winning_ask_bid_id: str
    original_min_ask_total_inr: Optional[str] = None

    new_winning_ask_bid_id: Optional[str] = None
    new_min_ask_total_inr: Optional[str] = None

    comp_dcu_units: Optional[str] = None
    comp_ask_price_per_unit_inr: Optional[str] = None

    notes: Dict[str, Any] = Field(default_factory=dict)
