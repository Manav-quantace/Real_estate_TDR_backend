from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.core.types import WorkflowType


class AuditLogRecordResponse(BaseModel):
    id: str
    createdAtIso: str
    requestId: str
    route: str
    method: str

    actorParticipantId: str
    actorRole: str

    workflow: WorkflowType
    projectId: str
    t: Optional[int] = None

    action: str
    status: str
    payloadHash: str
    payloadSummary: Dict[str, Any] = Field(default_factory=dict)
    refId: Optional[str] = None


class AuditLogListResponse(BaseModel):
    workflow: WorkflowType
    projectId: str
    t: Optional[int] = None
    records: List[AuditLogRecordResponse]
