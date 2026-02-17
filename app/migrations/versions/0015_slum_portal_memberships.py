"""slum portal memberships

Revision ID: 0015_slum_portal_memberships
Revises: 0014_projects_publish_fields
Create Date: 2025-12-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0015_slum_portal_memberships"
down_revision = "0014_projects_publish_fields"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "slum_portal_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),

        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),

        sa.Column("participant_id", sa.String(length=128), nullable=False),
        sa.Column("portal_type", sa.String(length=64), nullable=False),

        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),

        sa.UniqueConstraint("workflow", "project_id", "participant_id", "portal_type", name="uq_slum_portal_member"),
    )
    op.create_index("ix_slum_portal_scope", "slum_portal_memberships", ["workflow", "project_id", "portal_type"])
    op.create_index("ix_slum_portal_participant", "slum_portal_memberships", ["participant_id"])


def downgrade():
    op.drop_index("ix_slum_portal_participant", table_name="slum_portal_memberships")
    op.drop_index("ix_slum_portal_scope", table_name="slum_portal_memberships")
    op.drop_table("slum_portal_memberships")
