# /app/models/project.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import String, DateTime, Boolean, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    workflow: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(
        String(64), nullable=False, server_default=text("'draft'")
    )

    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    metadata_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    # ✅ REQUIRED for Round.back_populates
    rounds = relationship(
        "Round",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    subsidized_models = relationship(
        "SubsidizedEconomicModel",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    __table_args__ = (Index("ix_projects_workflow_status", "workflow", "status"),)
