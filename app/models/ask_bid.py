# app/models/ask_bid.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    String, DateTime, Integer, ForeignKey, UniqueConstraint, Index, text, Numeric
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AskBid(Base):
    __tablename__ = "ask_bids"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    workflow: Mapped[str] = mapped_column(String(32), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    round_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rounds.id", ondelete="CASCADE"), nullable=False)
    t: Mapped[int] = mapped_column(Integer, nullable=False)

    participant_id: Mapped[str] = mapped_column(String(128), nullable=False)

    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'draft'"))

    # DCU columns (separate columns as requested)
    dcu_units: Mapped[Optional[float]] = mapped_column(Numeric(20, 4), nullable=True)
    ask_price_per_unit_inr: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    total_ask_inr: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)

    # Compensatory DCU columns
    comp_dcu_units: Mapped[Optional[float]] = mapped_column(Numeric(20, 4), nullable=True)
    comp_ask_price_per_unit_inr: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)

    # ΔBid storage
    delta_ask_next_round_inr: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)

    # DCU-only payload (and compensatory DCU fields) per your rule
    payload_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    signature_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("workflow", "project_id", "t", "participant_id", name="uq_ask_bid_scope"),
        Index("ix_ask_bid_lookup", "workflow", "project_id", "t"),
        Index("ix_ask_bid_round", "round_id"),
    )
