#app/models/subsidized_valuation.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Integer, Numeric, ForeignKey, UniqueConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SubsidizedValuationRecord(Base):
    """
    Independent Valuer Valuation for subsidized workflow projects.

    Immutability:
      - Append-only. New valuation writes a new version row.
      - BUT: If project is published => valuation becomes read-only (no new versions).
    """
    __tablename__ = "subsidized_valuation_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    workflow: Mapped[str] = mapped_column(String(32), nullable=False)  # must be "subsidized"
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    version: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..N per project

    # Field: Independent Valuer Valuation
    valuation_inr: Mapped[Optional[float]] = mapped_column(Numeric(20, 2), nullable=True)

    # status
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # not_submitted / submitted / verified

    # timestamp + signed-by
    valued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))
    signed_by_participant_id: Mapped[str] = mapped_column(String(128), nullable=False)

    # Optional: verifier fields (kept structural)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_participant_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    __table_args__ = (
        UniqueConstraint("workflow", "project_id", "version", name="uq_subsidized_val_version"),
        Index("ix_subsidized_val_scope", "workflow", "project_id"),
        Index("ix_subsidized_val_status", "status"),
    )