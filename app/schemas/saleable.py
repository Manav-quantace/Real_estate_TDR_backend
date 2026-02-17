from pydantic import BaseModel
from typing import Dict, Any, Literal, Optional
from datetime import datetime


# ----------------------------
# CREATE
# ----------------------------
class SaleableCreate(BaseModel):
    title: str
    params: Dict[str, Any]
    action: Literal["save", "publish"]


# ----------------------------
# UPDATE
# ----------------------------
class SaleableUpdate(BaseModel):
    params: Dict[str, Any]
    action: Literal["save", "publish"] = "save"


# ----------------------------
# READ (DETAIL)
# ----------------------------
class SaleableProjectOut(BaseModel):
    project_id: str
    title: str
    status: str
    is_published: bool
    published_at: Optional[datetime]
    params: Dict[str, Any]

    model_config = {
        "from_attributes": True
    }
