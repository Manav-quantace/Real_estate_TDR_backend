# app/models/matching_result.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    String,
    DateTime,
    Integer,
    ForeignKey,
    Numeric,
    UniqueConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MatchingResult(Base):
    __tablename__ = "matching_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    workflow: Mapped[str] = mapped_column(String(32), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    round_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rounds.id", ondelete="CASCADE"), nullable=False
    )
    t: Mapped[int] = mapped_column(Integer, nullable=False)

    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    status: Mapped[str] = mapped_column(
        String(32), nullable=False, server_default=text("'computed'")
    )
    matched: Mapped[bool] = mapped_column(
        String(5), nullable=False, server_default=text("'false'")
    )

    # Selected bids (ids only; not full list)
    selected_ask_bid_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    selected_quote_bid_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )

    # Key values used (auditable)
    min_ask_total_inr: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )
    max_quote_inr: Mapped[Optional[float]] = mapped_column(
        Numeric(20, 2), nullable=True
    )

    # Optional explanation payload (no participant lists)
    notes_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    __table_args__ = (
        UniqueConstraint(
            "workflow", "project_id", "t", name="uq_matching_result_scope"
        ),
        Index("ix_matching_result_lookup", "workflow", "project_id", "t"),
        Index("ix_matching_result_round", "round_id"),
    )
