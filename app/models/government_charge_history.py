#app/models/government_charge_history.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    String, DateTime, Numeric, ForeignKey, Index, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class GovernmentChargeHistory(Base):
    """
    Immutable history rows when a GovernmentCharge is recalculated.
    We store the previous (weights, inputs, value_inr) and metadata.
    """
    __tablename__ = "government_charge_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    charge_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("government_charges.id", ondelete="CASCADE"), nullable=False)

    workflow: Mapped[str] = mapped_column(String(32), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    round_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    charge_type: Mapped[str] = mapped_column(String(8), nullable=False)  # GC / GCU

    weights_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    inputs_json: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    value_inr: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)

    replaced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    replaced_by_participant_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    __table_args__ = (
        Index("ix_gch_workflow_project_round_type", "workflow", "project_id", "round_id", "charge_type"),
        Index("ix_gch_replaced_at", "replaced_at"),
    )

