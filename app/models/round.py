#app/models/round.py
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
    CheckConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import RoundState
import sqlalchemy as sa


class Round(Base):
    __tablename__ = "rounds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    workflow: Mapped[str] = mapped_column(String(32), nullable=False)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    t: Mapped[int] = mapped_column(Integer, nullable=False)

    state: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default=text(f"'{RoundState.draft.value}'")
    )

    bidding_window_start: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    bidding_window_end: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    is_open: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=text("false"))
    is_locked: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=text("false"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    project = relationship("Project", back_populates="rounds")

    # ✅ ONE inventory per round
    unit_inventory = relationship(
        "UnitInventory",
        back_populates="round",
        cascade="all, delete-orphan",
        uselist=False,
    )

    government_charges = relationship(
        "GovernmentCharge", back_populates="round", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("workflow", "project_id", "t", name="uq_rounds_workflow_project_t"),
        CheckConstraint("t >= 0", name="ck_rounds_t_nonnegative"),
        Index("ix_rounds_workflow_project_state", "workflow", "project_id", "state"),
        Index("ix_rounds_workflow_project_t", "workflow", "project_id", "t"),
    )
