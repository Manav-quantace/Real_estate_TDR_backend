from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    DateTime,
    Integer,
    ForeignKey,
    UniqueConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DeveloperDefaultEvent(Base):
    __tablename__ = "developer_default_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    workflow: Mapped[str] = mapped_column(String(32), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    round_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rounds.id", ondelete="CASCADE"), nullable=False
    )
    t: Mapped[int] = mapped_column(Integer, nullable=False)

    # Default declared for the winning ASK bid (developer side)
    winning_ask_bid_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    declared_by_participant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    declared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        UniqueConstraint("workflow", "project_id", "t", name="uq_dev_default_scope"),
        Index("ix_dev_default_lookup", "workflow", "project_id", "t"),
    )
