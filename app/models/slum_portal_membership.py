#app/models/slum_portal_membership.py
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, UniqueConstraint, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SlumPortalMembership(Base):
    """
    Explicit participant membership by portal for slum projects (tripartite).
    """
    __tablename__ = "slum_portal_memberships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    workflow: Mapped[str] = mapped_column(String(32), nullable=False)  # must be "slum"
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    participant_id: Mapped[str] = mapped_column(String(128), nullable=False)

    # Exactly 3 portal types
    portal_type: Mapped[str] = mapped_column(String(64), nullable=False)  # SLUM_DWELLER | SLUM_LAND_DEVELOPER | AFFORDABLE_HOUSING_DEV

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("now()"))

    __table_args__ = (
        UniqueConstraint("workflow", "project_id", "participant_id", "portal_type", name="uq_slum_portal_member"),
        Index("ix_slum_portal_scope", "workflow", "project_id", "portal_type"),
        Index("ix_slum_portal_participant", "participant_id"),
    )