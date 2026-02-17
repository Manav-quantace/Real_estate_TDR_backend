"""audit log records

Revision ID: 0013_audit_log_records
Revises: 0012_tokenized_contract_and_ledger
Create Date: 2025-12-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013_audit_log_records"
down_revision = "0012_tokenized_contract_and_ledger"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "audit_log_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),

        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column("route", sa.String(length=256), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),

        sa.Column("actor_participant_id", sa.String(length=128), nullable=False),
        sa.Column("actor_role", sa.String(length=64), nullable=False),

        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("t", sa.Integer(), nullable=True),

        sa.Column("action", sa.String(length=96), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'ok'")),

        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("payload_summary_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),

        sa.Column("ref_id", sa.String(length=128), nullable=True),
    )

    op.create_index("ix_audit_scope", "audit_log_records", ["workflow", "project_id"])
    op.create_index("ix_audit_scope_t", "audit_log_records", ["workflow", "project_id", "t"])
    op.create_index("ix_audit_action", "audit_log_records", ["action"])
    op.create_index("ix_audit_created", "audit_log_records", ["created_at"])
    op.create_index("ix_audit_request_id", "audit_log_records", ["request_id"])


def downgrade():
    op.drop_index("ix_audit_request_id", table_name="audit_log_records")
    op.drop_index("ix_audit_created", table_name="audit_log_records")
    op.drop_index("ix_audit_action", table_name="audit_log_records")
    op.drop_index("ix_audit_scope_t", table_name="audit_log_records")
    op.drop_index("ix_audit_scope", table_name="audit_log_records")
    op.drop_table("audit_log_records")