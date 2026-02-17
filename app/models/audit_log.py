from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import String, DateTime, Integer, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditLogRecord(Base):
    """
    Comprehensive audit trail record.
    - Append-only (never UPDATE)
    - Stores request-id, actor, workflow/project/t, action, payload hash, and safe payload summary.
    """
    __tablename__ = "audit_log_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    # Correlation
    request_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    route: Mapped[str] = mapped_column(String(256), nullable=False)
    method: Mapped[str] = mapped_column(String(16), nullable=False)

    # Actor / auth context (store participant_id + role as string)
    actor_participant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(64), nullable=False)

    # Strict scoping
    workflow: Mapped[str] = mapped_column(String(32), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    t: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # some actions may not be round-specific

    # What happened
    action: Mapped[str] = mapped_column(String(96), nullable=False)  # e.g., BID_SUBMITTED_QUOTE
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'ok'"))

    # Payload traceability (hash + safe summary)
    payload_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_summary_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    # Optional result reference ids
    ref_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    __table_args__ = (
        Index("ix_audit_scope", "workflow", "project_id"),
        Index("ix_audit_scope_t", "workflow", "project_id", "t"),
        Index("ix_audit_action", "action"),
        Index("ix_audit_created", "created_at"),
    )
    
    
    
class AuditLog(Base):
    """
    Minimal audit log table for Part 6.
    Full ledger/audit module is Part 19, but Part 6 requires audit history now.
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    workflow: Mapped[str] = mapped_column(String(32), nullable=False)
    project_id: Mapped[str] = mapped_column(String(64), nullable=False)  # keep string for flexible refs
    t: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    actor_participant_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)

    request_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    details_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        Index("ix_audit_workflow_project_t", "workflow", "project_id", "t"),
        Index("ix_audit_created_at", "created_at"),
    )

###changes made  may conflict