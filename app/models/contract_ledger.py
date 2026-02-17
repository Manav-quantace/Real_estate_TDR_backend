# app/models/contract_ledger.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict

from sqlalchemy import (
    String,
    DateTime,
    Integer,
    ForeignKey,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ContractLedgerEntry(Base):
    """
    Append-only hash-chained ledger entries.

    entry_hash = SHA256(prev_hash + canonical(payload_json))
    """

    __tablename__ = "contract_ledger_entries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    workflow: Mapped[str] = mapped_column(String(32), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tokenized_contract_records.id", ondelete="CASCADE"),
        nullable=False,
    )

    seq: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # monotonic per (workflow, projectId)
    entry_type: Mapped[str] = mapped_column(String(64), nullable=False)

    prev_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    payload_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    __table_args__ = (
        UniqueConstraint(
            "workflow", "project_id", "seq", name="uq_contract_ledger_seq"
        ),
        Index("ix_contract_ledger_scope", "workflow", "project_id"),
        Index("ix_contract_ledger_contract", "contract_id"),
    )
