from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    String,
    DateTime,
    Integer,
    ForeignKey,
    UniqueConstraint,
    Index,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ParameterSnapshot(Base):
    __tablename__ = "parameter_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    workflow: Mapped[str] = mapped_column(String(32), nullable=False)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    t: Mapped[int] = mapped_column(Integer, nullable=False)

    payload_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )

    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
    )

    published_by_participant_id: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint(
            "workflow",
            "project_id",
            "t",
            name="uq_parameter_snapshots_workflow_project_t",
        ),
        Index(
            "ix_parameter_snapshots_workflow_project_t",
            "workflow",
            "project_id",
            "t",
        ),
        Index("ix_parameter_snapshots_published_at", "published_at"),
    )
