from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import String, DateTime, UniqueConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IdempotencyKeyRecord(Base):
    """
    Stores response for a POST request with Idempotency-Key header to prevent duplicates.

    Scope is strict:
      (workflow, project_id, participant_id, endpoint_key, idem_key) must be unique.
    """
    __tablename__ = "idempotency_key_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    workflow: Mapped[str] = mapped_column(String(32), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    participant_id: Mapped[str] = mapped_column(String(128), nullable=False)

    endpoint_key: Mapped[str] = mapped_column(String(64), nullable=False)  # e.g. "POST:/v1/bids/quote"
    idem_key: Mapped[str] = mapped_column(String(128), nullable=False)

    request_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    response_status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'200'"))
    response_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        UniqueConstraint("workflow", "project_id", "participant_id", "endpoint_key", "idem_key", name="uq_idem_scope"),
        Index("ix_idem_lookup", "workflow", "project_id", "participant_id", "endpoint_key"),
    )