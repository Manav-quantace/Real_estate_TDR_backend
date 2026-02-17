"""idempotency key records

Revision ID: 0017_idempotency_keys
Revises: 0016_subsidized_valuation_records
Create Date: 2025-12-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0017_idempotency_keys"
down_revision = "0016_subsidized_valuation_records"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "idempotency_key_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),

        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("participant_id", sa.String(length=128), nullable=False),

        sa.Column("endpoint_key", sa.String(length=64), nullable=False),
        sa.Column("idem_key", sa.String(length=128), nullable=False),

        sa.Column("request_hash", sa.String(length=128), nullable=False),

        sa.Column("response_status", sa.String(length=16), nullable=False, server_default=sa.text("'200'")),
        sa.Column("response_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),

        sa.UniqueConstraint("workflow", "project_id", "participant_id", "endpoint_key", "idem_key", name="uq_idem_scope"),
    )
    op.create_index("ix_idem_lookup", "idempotency_key_records", ["workflow", "project_id", "participant_id", "endpoint_key"])


def downgrade():
    op.drop_index("ix_idem_lookup", table_name="idempotency_key_records")
    op.drop_table("idempotency_key_records")
