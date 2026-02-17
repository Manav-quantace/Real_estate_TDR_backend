"""event log + developer default + developer compensatory events

Revision ID: 0011_dev_compensatory_two_tier
Revises: 0010_compensatory_events
Create Date: 2025-12-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011_dev_compensatory_two_tier"
down_revision = "0010_compensatory_events"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "event_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("t", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("actor_participant_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("payload_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    op.create_index("ix_event_logs_scope", "event_logs", ["workflow", "project_id", "t"])
    op.create_index("ix_event_logs_type", "event_logs", ["event_type"])

    op.create_table(
        "developer_default_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("round_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("t", sa.Integer(), nullable=False),
        sa.Column("winning_ask_bid_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("declared_by_participant_id", sa.String(length=128), nullable=False),
        sa.Column("reason", sa.String(length=512), nullable=True),
        sa.Column("declared_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("workflow", "project_id", "t", name="uq_dev_default_scope"),
    )
    op.create_index("ix_dev_default_lookup", "developer_default_events", ["workflow", "project_id", "t"])

    op.create_table(
        "developer_compensatory_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("round_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("t", sa.Integer(), nullable=False),

        sa.Column("settlement_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("developer_default_event_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("status", sa.String(length=64), nullable=False, server_default=sa.text("'computed'")),

        sa.Column("original_winning_ask_bid_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_min_ask_total_inr", sa.Numeric(20, 2), nullable=True),

        sa.Column("new_winning_ask_bid_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("new_min_ask_total_inr", sa.Numeric(20, 2), nullable=True),

        sa.Column("comp_dcu_units", sa.Numeric(20, 4), nullable=True),
        sa.Column("comp_ask_price_per_unit_inr", sa.Numeric(20, 2), nullable=True),

        sa.Column("notes_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),

        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["settlement_result_id"], ["settlement_results.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["developer_default_event_id"], ["developer_default_events.id"], ondelete="CASCADE"),

        sa.UniqueConstraint("workflow", "project_id", "t", name="uq_dev_comp_scope"),
    )
    op.create_index("ix_dev_comp_lookup", "developer_compensatory_events", ["workflow", "project_id", "t"])


def downgrade():
    op.drop_index("ix_dev_comp_lookup", table_name="developer_compensatory_events")
    op.drop_table("developer_compensatory_events")

    op.drop_index("ix_dev_default_lookup", table_name="developer_default_events")
    op.drop_table("developer_default_events")

    op.drop_index("ix_event_logs_type", table_name="event_logs")
    op.drop_index("ix_event_logs_scope", table_name="event_logs")
    op.drop_table("event_logs")
