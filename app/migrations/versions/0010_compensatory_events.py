"""compensatory events

Revision ID: 0010_compensatory_events
Revises: 0009_default_and_penalty_events
Create Date: 2025-12-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_compensatory_events"
down_revision = "0009_default_and_penalty_events"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "compensatory_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("round_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("t", sa.Integer(), nullable=False),

        sa.Column("settlement_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("default_event_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.String(length=64), nullable=False, server_default=sa.text("'computed'")),

        sa.Column("original_winner_quote_bid_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_second_quote_bid_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_bsecond_inr", sa.Numeric(20, 2), nullable=False),

        sa.Column("new_winner_quote_bid_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("new_second_quote_bid_id", postgresql.UUID(as_uuid=True), nullable=True),

        sa.Column("bsecond_new_raw_inr", sa.Numeric(20, 2), nullable=True),
        sa.Column("bsecond_new_enforced_inr", sa.Numeric(20, 2), nullable=True),

        sa.Column("enforcement_action", sa.String(length=64), nullable=False, server_default=sa.text("'none'")),
        sa.Column("notes_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),

        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["settlement_result_id"], ["settlement_results.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["default_event_id"], ["default_events.id"], ondelete="CASCADE"),

        sa.UniqueConstraint("workflow", "project_id", "t", name="uq_comp_event_scope"),
    )
    op.create_index("ix_comp_event_lookup", "compensatory_events", ["workflow", "project_id", "t"])


def downgrade():
    op.drop_index("ix_comp_event_lookup", table_name="compensatory_events")
    op.drop_table("compensatory_events")
