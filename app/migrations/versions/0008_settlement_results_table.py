"""settlement results table

Revision ID: 0008_settlement_results_table
Revises: 0007_matching_results_table
Create Date: 2025-12-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0008_settlement_results_table"
down_revision = "0007_matching_results_table"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "settlement_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("round_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("t", sa.Integer(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'computed'")),
        sa.Column("matching_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("settled", sa.String(length=5), nullable=False, server_default=sa.text("'false'")),

        sa.Column("winner_quote_bid_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("winning_ask_bid_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("second_price_quote_bid_id", postgresql.UUID(as_uuid=True), nullable=True),

        sa.Column("max_quote_inr", sa.Numeric(20, 2), nullable=True),
        sa.Column("second_price_inr", sa.Numeric(20, 2), nullable=True),
        sa.Column("min_ask_total_inr", sa.Numeric(20, 2), nullable=True),

        sa.Column("receipt_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),

        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["matching_result_id"], ["matching_results.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("workflow", "project_id", "t", name="uq_settlement_result_scope"),
    )
    op.create_index("ix_settlement_result_lookup", "settlement_results", ["workflow", "project_id", "t"])
    op.create_index("ix_settlement_result_round", "settlement_results", ["round_id"])


def downgrade():
    op.drop_index("ix_settlement_result_round", table_name="settlement_results")
    op.drop_index("ix_settlement_result_lookup", table_name="settlement_results")
    op.drop_table("settlement_results")