from __future__ import annotations

from typing import Optional, List

from pydantic import BaseModel, Field

from app.schemas.primitives import ScopedRef


class ImmutableEventLog(BaseModel):
    event_id: str
    timestamp_iso: str
    event_type: str
    actor: str
    ref: dict = Field(default_factory=dict)


class TokenizedContractRecord(ScopedRef):
    """
    Tokenized contract record (API-driven).
    Ownership details + transaction data + obligations + immutable event logs.
    """
    contract_id: str
    version: str = "1.0"
    published_at_iso: Optional[str] = None

    ownership_details: dict = Field(default_factory=dict)
    transaction_data: dict = Field(default_factory=dict)
    obligations: list = Field(default_factory=list)

    immutable_event_logs: List[ImmutableEventLog] = Field(default_factory=list)

    links: dict = Field(default_factory=dict, description="links to settlement/audit/etc")
    record_hash: Optional[str] = Field(default=None, description="optional hash for immutability")


class AuditLogRecord(ScopedRef):
    """
    Audit log record (append-only; API-driven).
    """
    audit_id: str
    timestamp_iso: str
    actor: str
    action: str
    t: Optional[int] = Field(default=None, ge=0)
    request_id: Optional[str] = None
    payload_hash: Optional[str] = None
    details: dict = Field(default_factory=dict)
