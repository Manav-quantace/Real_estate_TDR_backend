from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime


class AskBidUpsert(BaseModel):
    dcu_units: float
    ask_price_per_unit_inr: float
    action: Literal["save", "submit"]


class AskBidOut(BaseModel):
    state: str
    dcu_units: Optional[float]
    ask_price_per_unit_inr: Optional[float]
    total_ask_inr: Optional[float]
    submitted_at: Optional[datetime]
    locked_at: Optional[datetime]

    model_config = {"from_attributes": True}


class DeveloperAskPageOut(BaseModel):
    project: dict
    round: dict
    ask_bid: Optional[AskBidOut]
