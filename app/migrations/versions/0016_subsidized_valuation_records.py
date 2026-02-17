"""subsidized valuation records

Revision ID: 0016_subsidized_valuation_records
Revises: 0015_slum_portal_memberships
Create Date: 2025-12-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0016_subsidized_valuation_records"
down_revision = "0015_slum_portal_memberships"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "subsidized_valuation_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),

        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("version", sa.Integer(), nullable=False),

        sa.Column("valuation_inr", sa.Numeric(20, 2), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),

        sa.Column("valued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("signed_by_participant_id", sa.String(length=128), nullable=False),

        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by_participant_id", sa.String(length=128), nullable=True),

        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("workflow", "project_id", "version", name="uq_subsidized_val_version"),
    )

    op.create_index("ix_subsidized_val_scope", "subsidized_valuation_records", ["workflow", "project_id"])
    op.create_index("ix_subsidized_val_status", "subsidized_valuation_records", ["status"])


def downgrade():
    op.drop_index("ix_subsidized_val_status", table_name="subsidized_valuation_records")
    op.drop_index("ix_subsidized_val_scope", table_name="subsidized_valuation_records")
    op.drop_table("subsidized_valuation_records")