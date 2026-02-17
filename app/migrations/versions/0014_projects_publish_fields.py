"""project publish fields + status

Revision ID: 0014_projects_publish_fields
Revises: 0013_audit_log_records
Create Date: 2025-12-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0014_projects_publish_fields"
down_revision = "0013_audit_log_records"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("projects", sa.Column("status", sa.String(length=64), nullable=False, server_default=sa.text("'draft'")))
    op.add_column("projects", sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("projects", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("projects", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")))
    op.create_index("ix_projects_workflow_status", "projects", ["workflow", "status"])


def downgrade():
    op.drop_index("ix_projects_workflow_status", table_name="projects")
    op.drop_column("projects", "updated_at")
    op.drop_column("projects", "published_at")
    op.drop_column("projects", "is_published")
    op.drop_column("projects", "status")