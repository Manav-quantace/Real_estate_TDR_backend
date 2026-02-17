from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from app.schemas.primitives import BidRound, ScopedRef
from app.schemas.primitives import GC, GCU


class PublishedParamsSnapshot(BaseModel):
    """
    A published snapshot for a particular round t.
    """
    t: int = Field(..., ge=0)
    round: BidRound
    inventory: Dict[str, Any] = Field(default_factory=dict, description="LU/TDRU/PRU/DCU snapshot (structural)")
    government_charges: Dict[str, Any] = Field(default_factory=dict, description="GC/GCU placeholders or values (structural)")
    published_at_iso: Optional[str] = None


class ParamsInitResponse(ScopedRef):
    """
    Response of GET /params/init: snapshot for t=0 and for current round.
    No private bid details, only published parameters.
    """
    t0: PublishedParamsSnapshot
    current: PublishedParamsSnapshot
    visibility: str = Field(..., description="PUBLIC or AUTHORITY/AUDITOR enhanced view")
