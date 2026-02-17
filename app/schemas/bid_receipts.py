from __future__ import annotations

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.core.types import WorkflowType


class BidReceipt(BaseModel):
    receipt_id: str
    workflow: WorkflowType
    projectId: str
    t: int = Field(..., ge=0)
    bidId: str
    status: str = Field(..., description="stored_draft | stored_submitted | rejected")
    signature_hash: Optional[str] = None


class MyBidRecord(BaseModel):
    bidId: str
    bid_type: str = Field(..., description="QUOTE")
    t: int = Field(..., ge=0)
    state: str = Field(..., description="draft|submitted|locked")
    submitted_at_iso: Optional[str] = None
    locked_at_iso: Optional[str] = None
    # Return only the payload the user submitted (their own), never anyone else's.
    payload: Dict[str, Any] = Field(default_factory=dict)


class MyBidsResponse(BaseModel):
    workflow: WorkflowType
    projectId: str
    t: int = Field(..., ge=0)
    bids: List[MyBidRecord] = Field(default_factory=list)
