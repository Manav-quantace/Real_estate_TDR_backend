#app/models/government_charge.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    ForeignKeyConstraint,
    String,
    DateTime,
    Numeric,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ChargeType


class GovernmentCharge(Base):
    """
    Stores GC / GCU structural inputs and (optional) computed values later.
    Part 2: no computation, only storage fields.
    """

    __tablename__ = "government_charges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    workflow: Mapped[str] = mapped_column(String(32), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    round_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    charge_type: Mapped[str] = mapped_column(String(8), nullable=False)  # GC or GCU

    # structural storage:
    # weights (α, β, γ, etc) and inputs (EC, MC, HD, PVIC, LUOS, r, etc) are stored as JSONB
    weights_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    inputs_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    # optional output value (may be computed in later part)
    value_inr: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    round = relationship("Round", back_populates="government_charges")

    __table_args__ = (
        
        ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            name="fk_government_charges_round",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "workflow",
            "project_id",
            "round_id",
            "charge_type",
            name="uq_gov_charge_workflow_project_round_type",
        ),
        CheckConstraint(
            "value_inr IS NULL OR value_inr >= 0", name="ck_gov_charge_value_nonneg"
        ),
        Index(
            "ix_gov_charge_workflow_project_round", "workflow", "project_id", "round_id"
        ),
        Index("ix_gov_charge_type", "charge_type"),
    )
