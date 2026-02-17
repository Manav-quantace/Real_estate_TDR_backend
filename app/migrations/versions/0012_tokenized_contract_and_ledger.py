"""tokenized contract record + hash-chained ledger

Revision ID: 0012_tokenized_contract_and_ledger
Revises: 0011_dev_compensatory_two_tier
Create Date: 2025-12-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_tokenized_contract_and_ledger"
down_revision = "0011_dev_compensatory_two_tier"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tokenized_contract_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("prior_contract_id", postgresql.UUID(as_uuid=True), nullable=True),

        sa.Column("settlement_result_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),

        sa.Column("ownership_details_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("transaction_data_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("legal_obligations_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),

        sa.Column("contract_hash", sa.String(length=128), nullable=False),

        sa.ForeignKeyConstraint(["prior_contract_id"], ["tokenized_contract_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["settlement_result_id"], ["settlement_results.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("workflow", "project_id", "version", name="uq_contract_project_version"),
    )
    op.create_index("ix_contract_project_scope", "tokenized_contract_records", ["workflow", "project_id"])
    op.create_index("ix_contract_settlement", "tokenized_contract_records", ["settlement_result_id"])

    op.create_table(
        "contract_ledger_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("entry_type", sa.String(length=64), nullable=False),

        sa.Column("prev_hash", sa.String(length=128), nullable=False),
        sa.Column("entry_hash", sa.String(length=128), nullable=False),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("payload_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),

        sa.ForeignKeyConstraint(["contract_id"], ["tokenized_contract_records.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("workflow", "project_id", "seq", name="uq_contract_ledger_seq"),
    )
    op.create_index("ix_contract_ledger_scope", "contract_ledger_entries", ["workflow", "project_id"])
    op.create_index("ix_contract_ledger_contract", "contract_ledger_entries", ["contract_id"])


def downgrade():
    op.drop_index("ix_contract_ledger_contract", table_name="contract_ledger_entries")
    op.drop_index("ix_contract_ledger_scope", table_name="contract_ledger_entries")
    op.drop_table("contract_ledger_entries")

    op.drop_index("ix_contract_settlement", table_name="tokenized_contract_records")
    op.drop_index("ix_contract_project_scope", table_name="tokenized_contract_records")
    op.drop_table("tokenized_contract_records")
