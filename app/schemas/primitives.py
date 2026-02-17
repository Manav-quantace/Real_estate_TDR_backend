from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Optional

from pydantic import BaseModel, Field
from pydantic import condecimal, conint, constr

from app.core.types import WorkflowType


# --- Numeric primitives (structural) ---
NonNegDec4 = Annotated[Decimal, condecimal(ge=0, max_digits=20, decimal_places=4)]
MoneyINR = Annotated[Decimal, condecimal(ge=0, max_digits=20, decimal_places=2)]
NonNegInt = Annotated[int, conint(ge=0)]


# --- Unit types (strict terminology) ---
class LU(BaseModel):
    value: NonNegDec4 = Field(..., description="LU units (structural)")


class TDRU(BaseModel):
    value: NonNegDec4 = Field(..., description="TDRU units (structural)")


class PRU(BaseModel):
    value: NonNegDec4 = Field(..., description="PRU units (structural)")


class DCU(BaseModel):
    value: NonNegDec4 = Field(..., description="DCU units (structural)")


class Qbundle(BaseModel):
    value: MoneyINR = Field(..., description="Bundle quote amount (INR) (structural)")


class Qnet(BaseModel):
    value: MoneyINR = Field(..., description="Net quote after charges (structural, API-provided)")


class GC(BaseModel):
    """
    Government Charge (structural): weights + inputs + optional computed value.
    No formula computation here.
    """
    weights: dict = Field(default_factory=dict, description="α, β, γ etc as published by authority")
    inputs: dict = Field(default_factory=dict, description="EC, MC, HD etc as published/derived")
    value_inr: Optional[MoneyINR] = Field(default=None, description="Computed GC value in INR, if provided by API")


class GCU(BaseModel):
    """
    Green Charge Unit (structural): weights + inputs + optional computed value.
    No formula computation here.
    """
    weights: dict = Field(default_factory=dict, description="α, β, γ etc")
    inputs: dict = Field(default_factory=dict, description="PVIC, LUOS, r etc")
    value_inr: Optional[MoneyINR] = Field(default=None, description="Computed GCU value in INR, if provided by API")


class BidRound(BaseModel):
    """
    Iterative round t structure.
    """
    id: str          
    t: NonNegInt = Field(..., description="Round index t")
    state: str = Field(..., description="draft | submitted | locked (structural)")
    bidding_window_start: Optional[str] = Field(default=None, description="ISO timestamp string")
    bidding_window_end: Optional[str] = Field(default=None, description="ISO timestamp string")
    is_open: bool = Field(default=False)
    is_locked: bool = Field(default=False)


class ScopedRef(BaseModel):
    """
    Mandatory workflow scope for bids/results/events/ledger.
    """
    workflow: WorkflowType
    projectId: constr(min_length=1, max_length=128)
