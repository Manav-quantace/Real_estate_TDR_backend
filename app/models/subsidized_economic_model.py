from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, Numeric, DateTime, Boolean, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SubsidizedEconomicModel(Base):
    __tablename__ = "subsidized_economic_models"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_published_version: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    # ── POLICY INPUTS ─────────────────────────────
    lu_total: Mapped[int] = mapped_column(Integer, nullable=False)
    lu_open_space: Mapped[int] = mapped_column(Integer, nullable=False)

    pvic: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)

    alpha: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    beta: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    gamma: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)

    # ── DERIVED VALUES ────────────────────────────
    ec: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    gci: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    gce: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)
    gcu: Mapped[float] = mapped_column(Numeric(20, 2), nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    project = relationship("Project", back_populates="subsidized_models")

    __table_args__ = (
        Index("ix_subsidized_model_proj_ver", "project_id", "version", unique=True),
    )
