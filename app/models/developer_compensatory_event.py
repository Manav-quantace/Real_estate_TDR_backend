from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import String, DateTime, Integer, ForeignKey, Numeric, UniqueConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DeveloperCompensatoryEvent(Base):
    __tablename__ = "developer_compensatory_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    workflow: Mapped[str] = mapped_column(String(32), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    round_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("rounds.id", ondelete="CASCADE"), nullable=False)
    t: Mapped[int] = mapped_column(Integer, nullable=False)

    # Linkage to settlement + default (developer side)
    settlement_result_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("settlement_results.id", ondelete="CASCADE"), nullable=False)
    developer_default_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("developer_default_events.id", ondelete="CASCADE"), nullable=False)

    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    status: Mapped[str] = mapped_column(String(64), nullable=False, server_default=text("'computed'"))

    # Original winner (developer ask bid)
    original_winning_ask_bid_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    original_min_ask_total_inr: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)

    # New allocation (next eligible developer ask)
    new_winning_ask_bid_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    new_min_ask_total_inr: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)

    # Compensatory payout reference from stored *compensatory* ask fields (no hidden computation)
    comp_dcu_units: Mapped[Optional[float]] = mapped_column(Numeric(20, 4), nullable=True)
    comp_ask_price_per_unit_inr: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)

    notes_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    __table_args__ = (
        UniqueConstraint("workflow", "project_id", "t", name="uq_dev_comp_scope"),
        Index("ix_dev_comp_lookup", "workflow", "project_id", "t"),
    )
