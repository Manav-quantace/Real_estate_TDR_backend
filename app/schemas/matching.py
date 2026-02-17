from __future__ import annotations

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.core.types import WorkflowType


class MatchingResultResponse(BaseModel):
    workflow: WorkflowType
    projectId: str
    t: int = Field(..., ge=0)

    status: str
    matched: bool

    selected_ask_bid_id: Optional[str] = None
    selected_quote_bid_id: Optional[str] = None

    min_ask_total_inr: Optional[str] = None
    max_quote_inr: Optional[str] = None

    computed_at_iso: str
    notes: Dict[str, Any] = Field(default_factory=dict)