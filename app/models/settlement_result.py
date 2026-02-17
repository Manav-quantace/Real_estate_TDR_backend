#app/models/settlement_result.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    String, DateTime, Integer, ForeignKey, Numeric, UniqueConstraint, Index, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SettlementResult(Base):
    __tablename__ = "settlement_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    workflow: Mapped[str] = mapped_column(String(32), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    round_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rounds.id", ondelete="CASCADE"), nullable=False)
    t: Mapped[int] = mapped_column(Integer, nullable=False)

    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default=text("'computed'"))

    # Links to matching result (for traceability)
    matching_result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("matching_results.id", ondelete="CASCADE"), nullable=False)

    settled: Mapped[bool] = mapped_column(String(5), nullable=False, server_default=text("'false'"))

    # Winner / selected bids (ids)
    winner_quote_bid_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    winning_ask_bid_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Vickrey second price reference (explicitly stored)
    second_price_quote_bid_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Key amounts stored
    max_quote_inr: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    second_price_inr: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)
    min_ask_total_inr: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)

    # Traceability bundle: hashes, timestamps, role visibility markers, etc.
    receipt_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    __table_args__ = (
        UniqueConstraint("workflow", "project_id", "t", name="uq_settlement_result_scope"),
        Index("ix_settlement_result_lookup", "workflow", "project_id", "t"),
        Index("ix_settlement_result_round", "round_id"),
    )