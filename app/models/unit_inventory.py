# app/models/unit_inventory.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String, DateTime, Numeric, ForeignKey,
    UniqueConstraint, CheckConstraint, Index, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UnitInventory(Base):
    __tablename__ = "unit_inventories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    workflow: Mapped[str] = mapped_column(String(32), nullable=False)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    round_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rounds.id", ondelete="CASCADE"),
        nullable=False,
    )

    lu: Mapped[Optional[float]] = mapped_column(Numeric(20, 4), nullable=True)
    tdru: Mapped[Optional[float]] = mapped_column(Numeric(20, 4), nullable=True)
    pru: Mapped[Optional[float]] = mapped_column(Numeric(20, 4), nullable=True)
    dcu: Mapped[Optional[float]] = mapped_column(Numeric(20, 4), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    # ✅ ONLY via round
    round = relationship("Round", back_populates="unit_inventory")

    __table_args__ = (
        UniqueConstraint("round_id", name="uq_unit_inventory_round"),
        CheckConstraint("lu IS NULL OR lu >= 0", name="ck_unit_inventory_lu_nonneg"),
        CheckConstraint("tdru IS NULL OR tdru >= 0", name="ck_unit_inventory_tdru_nonneg"),
        CheckConstraint("pru IS NULL OR pru >= 0", name="ck_unit_inventory_pru_nonneg"),
        CheckConstraint("dcu IS NULL OR dcu >= 0", name="ck_unit_inventory_dcu_nonneg"),
        Index("ix_unit_inventory_scope", "workflow", "project_id", "round_id"),
    )
