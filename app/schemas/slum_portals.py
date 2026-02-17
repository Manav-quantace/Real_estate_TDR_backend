from __future__ import annotations
from typing import List, Dict
from pydantic import BaseModel, Field
from app.core.types import WorkflowType


class SlumPortalStatus(BaseModel):
    portalType: str
    enabled: bool
    member: bool


class SlumPortalsResponse(BaseModel):
    workflow: WorkflowType
    projectId: str
    portals: List[SlumPortalStatus] = Field(default_factory=list)