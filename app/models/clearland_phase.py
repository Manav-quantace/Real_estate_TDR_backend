# app/models/clearland_phase.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ClearlandPhase(Base):
    """
    Canonical phase state machine for clearland workflow.
    One active phase per project at any time.
    """

    __tablename__ = "clearland_phases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    phase: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        index=True,
        doc="Clearland phase identifier (e.g. INIT, DEVELOPER_ASK_OPEN)",
    )

    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    effective_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_by_participant_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    notes_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    # ─────────────────────────────────────────────
    # Constraints & indexes
    # ─────────────────────────────────────────────
    __table_args__ = (
        # Prevent duplicate identical phase records at same timestamp
        UniqueConstraint(
            "project_id",
            "phase",
            "effective_from",
            name="uq_clearland_phase_project_phase_from",
        ),
        Index(
            "ix_clearland_phase_project_active",
            "project_id",
            "effective_to",
        ),
    )
