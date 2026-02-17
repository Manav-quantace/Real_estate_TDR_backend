#app/models/clearland_project_memberships.py
from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Index, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ClearlandProjectMembership(Base):
    __tablename__ = "clearland_project_memberships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    participant_id: Mapped[str] = mapped_column(String(128), nullable=False)

    role: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        server_default=text("'active'"),
        doc="active | removed | suspended",
    )

    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "participant_id",
            name="uq_clearland_project_participant",
        ),
        Index("ix_clearland_membership_project", "project_id"),
    )
