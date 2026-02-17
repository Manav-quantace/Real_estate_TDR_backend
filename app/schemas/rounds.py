from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from app.core.types import WorkflowType
from app.schemas.primitives import BidRound


class RoundScope(BaseModel):
    workflow: WorkflowType
    projectId: str = Field(..., min_length=1)


class RoundOpenRequest(RoundScope):
    """
    Authority opens the next round.
    Optional explicit window end/start can be provided; if absent, start=now.
    """
    bidding_window_start_iso: Optional[str] = None
    bidding_window_end_iso: Optional[str] = None


class RoundCloseRequest(RoundScope):
    t: int = Field(..., ge=0)


class RoundLockRequest(RoundScope):
    t: int = Field(..., ge=0)


class RoundResponse(RoundScope):
    current: Optional[BidRound] = None