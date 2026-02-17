"""default + penalty events

Revision ID: 0009_default_and_penalty_events
Revises: 0008_settlement_results_table
Create Date: 2025-12-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_default_and_penalty_events"
down_revision = "0008_settlement_results_table"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "default_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("round_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("t", sa.Integer(), nullable=False),
        sa.Column("winner_quote_bid_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("declared_by_participant_id", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=True),
        sa.Column("declared_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("workflow", "project_id", "t", name="uq_default_event_scope"),
    )
    op.create_index("ix_default_event_lookup", "default_events", ["workflow", "project_id", "t"])

    op.create_table(
        "penalty_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("round_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("t", sa.Integer(), nullable=False),
        sa.Column("settlement_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("default_event_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("winner_quote_bid_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("second_price_quote_bid_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("bmax_inr", sa.Numeric(20, 2), nullable=False),
        sa.Column("bsecond_inr", sa.Numeric(20, 2), nullable=False),
        sa.Column("penalty_inr", sa.Numeric(20, 2), nullable=False),

        sa.Column("enforcement_status", sa.String(length=32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("notes_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),

        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["settlement_result_id"], ["settlement_results.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["default_event_id"], ["default_events.id"], ondelete="CASCADE"),

        sa.UniqueConstraint("workflow", "project_id", "t", name="uq_penalty_event_scope"),
    )
    op.create_index("ix_penalty_event_lookup", "penalty_events", ["workflow", "project_id", "t"])


def downgrade():
    op.drop_index("ix_penalty_event_lookup", table_name="penalty_events")
    op.drop_table("penalty_events")

    op.drop_index("ix_default_event_lookup", table_name="default_events")
    op.drop_table("default_events")