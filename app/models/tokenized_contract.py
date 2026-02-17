#app/models/tokenized_contract.py
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


class TokenizedContractRecord(Base):
    """
    TokenizedContractRecord = Blockchain(Ownership Details, Transaction Data, Legal Obligations)

    Immutability rule:
      - Never UPDATE a record.
      - Any change/extension creates a new record with version+1 and links to prior_contract_id.
    """

    __tablename__ = "tokenized_contract_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    workflow: Mapped[str] = mapped_column(String(32), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Versioning
    version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("1")
    )
    prior_contract_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tokenized_contract_records.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Trace links
    settlement_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("settlement_results.id", ondelete="RESTRICT"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    # Core structure: Ownership Details, Transaction Data, Legal Obligations
    ownership_details_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    transaction_data_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )
    legal_obligations_json: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    # Contract content hash (hash of canonical payload at creation time)
    contract_hash: Mapped[str] = mapped_column(String(128), nullable=False)

    __table_args__ = (
        Index("ix_contract_project_scope", "workflow", "project_id"),
        Index("ix_contract_settlement", "settlement_result_id"),
        UniqueConstraint(
            "workflow", "project_id", "version", name="uq_contract_project_version"
        ),
    )
