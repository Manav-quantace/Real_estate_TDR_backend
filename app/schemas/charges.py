from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from app.schemas.primitives import ScopedRef, MoneyINR


class ChargeResponse(ScopedRef):
    t: int = Field(..., ge=0)
    charge_type: str = Field(..., description="GC or GCU")
    weights: Dict[str, Any] = Field(default_factory=dict)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    value_inr: Optional[MoneyINR] = None
    calculated: bool = Field(default=False, description="true if computed now (recalc=true) or if value exists")
    audit_ref: Optional[str] = None
