from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey, Numeric, UniqueConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PenaltyEvent(Base):
    __tablename__ = "penalty_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    workflow: Mapped[str] = mapped_column(String(32), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    round_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rounds.id", ondelete="CASCADE"), nullable=False)
    t: Mapped[int] = mapped_column(Integer, nullable=False)

    # References
    settlement_result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("settlement_results.id", ondelete="CASCADE"), nullable=False)
    default_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("default_events.id", ondelete="CASCADE"), nullable=False)

    winner_quote_bid_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    second_price_quote_bid_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    # Exact values used
    bmax_inr: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    bsecond_inr: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    penalty_inr: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)

    enforcement_status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'pending'"))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    notes_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    __table_args__ = (
        UniqueConstraint("workflow", "project_id", "t", name="uq_penalty_event_scope"),
        Index("ix_penalty_event_lookup", "workflow", "project_id", "t"),
    )
