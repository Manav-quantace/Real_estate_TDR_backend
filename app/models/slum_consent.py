# app/models/slum_consent.py
from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class SlumConsent(Base):
    __tablename__ = "slum_consents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    workflow: Mapped[str] = mapped_column(String(16), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)

    participant_id: Mapped[str] = mapped_column(String(64), nullable=False)
    portal_type: Mapped[str] = mapped_column(String(32), nullable=False)

    consent_text: Mapped[str] = mapped_column(String, nullable=False)
    agreed: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
