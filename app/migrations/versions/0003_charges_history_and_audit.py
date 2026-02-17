"""gov charge history + audit logs

Revision ID: 0003_charges_history_and_audit
Revises: 0002_parameter_snapshots
Create Date: 2025-12-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_charges_history_and_audit"
down_revision = "0002_parameter_snapshots"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "government_charge_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("charge_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("round_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("charge_type", sa.String(length=8), nullable=False),
        sa.Column("weights_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("inputs_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("value_inr", sa.Numeric(20, 2), nullable=True),
        sa.Column("replaced_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("replaced_by_participant_id", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["charge_id"], ["government_charges.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_gch_workflow_project_round_type",
        "government_charge_history",
        ["workflow", "project_id", "round_id", "charge_type"],
    )
    op.create_index("ix_gch_replaced_at", "government_charge_history", ["replaced_at"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("t", sa.Integer(), nullable=True),
        sa.Column("actor_participant_id", sa.String(length=128), nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("details_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_workflow_project_t", "audit_logs", ["workflow", "project_id", "t"])
    op.create_index("ix_audit_created_at", "audit_logs", ["created_at"])


def downgrade():
    op.drop_index("ix_audit_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_workflow_project_t", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_gch_replaced_at", table_name="government_charge_history")
    op.drop_index("ix_gch_workflow_project_round_type", table_name="government_charge_history")
    op.drop_table("government_charge_history")