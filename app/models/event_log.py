#app/models/event_log.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import String, DateTime, Integer, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class EventLog(Base):
    __tablename__ = "event_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    workflow: Mapped[str] = mapped_column(String(32), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    t: Mapped[int] = mapped_column(Integer, nullable=False)

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_participant_id: Mapped[str] = mapped_column(String(128), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    payload_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    __table_args__ = (
        Index("ix_event_logs_scope", "workflow", "project_id", "t"),
        Index("ix_event_logs_type", "event_type"),
    )
