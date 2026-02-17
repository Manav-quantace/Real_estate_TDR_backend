from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, Field
from app.core.types import WorkflowType


class SubsidizedValuationUpsertRequest(BaseModel):
    workflow: WorkflowType
    projectId: str
    valuationInr: float = Field(..., ge=0)
    status: str = Field(..., pattern="^(submitted|verified)$")  # keep strict


class SubsidizedValuationResponse(BaseModel):
    workflow: WorkflowType
    projectId: str
    version: int
    valuationInr: Optional[str] = None
    status: str
    valuedAtIso: str
    signedByParticipantId: str
    verifiedAtIso: Optional[str] = None
    verifiedByParticipantId: Optional[str] = None


class SubsidizedValuationHistoryResponse(BaseModel):
    workflow: WorkflowType
    projectId: str
    latest: Optional[SubsidizedValuationResponse] = None
    history: List[SubsidizedValuationResponse] = Field(default_factory=list)