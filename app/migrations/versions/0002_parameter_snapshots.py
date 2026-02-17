"""parameter snapshots table

Revision ID: 0002_parameter_snapshots
Revises: 0001_core_domain
Create Date: 2025-12-13
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_parameter_snapshots"
down_revision = "0001_core_domain"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "parameter_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("t", sa.Integer(), nullable=False),
        sa.Column("payload_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("published_by_participant_id", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(
            ["workflow", "project_id"],
            ["projects.workflow", "projects.id"],
            name="fk_parameter_snapshots_project_workflow",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("workflow", "project_id", "t", name="uq_parameter_snapshots_workflow_project_t"),
    )
    op.create_index("ix_parameter_snapshots_workflow_project_t", "parameter_snapshots", ["workflow", "project_id", "t"])
    op.create_index("ix_parameter_snapshots_published_at", "parameter_snapshots", ["published_at"])


def downgrade():
    op.drop_index("ix_parameter_snapshots_published_at", table_name="parameter_snapshots")
    op.drop_index("ix_parameter_snapshots_workflow_project_t", table_name="parameter_snapshots")
    op.drop_table("parameter_snapshots")