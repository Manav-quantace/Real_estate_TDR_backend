from __future__ import annotations
from pydantic import BaseModel, Field
from app.core.types import WorkflowType


class SlumPortalEnrollRequest(BaseModel):
    workflow: WorkflowType
    projectId: str
    participantId: str = Field(..., min_length=1, max_length=128)
    portalType: str  # SLUM_DWELLER | SLUM_LAND_DEVELOPER | AFFORDABLE_HOUSING_DEV