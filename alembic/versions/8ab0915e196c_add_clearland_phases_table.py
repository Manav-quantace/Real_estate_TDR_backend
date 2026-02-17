"""add clearland phases table

Revision ID: 8ab0915e196c
Revises: 4e02a0fa1575
Create Date: 2026-02-12 23:57:55.532677

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8ab0915e196c'
down_revision: Union[str, Sequence[str], None] = '4e02a0fa1575'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "clearland_phases",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("phase", sa.String(length=32), nullable=False),
        sa.Column(
            "effective_from",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "effective_to",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_by_participant_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "notes_json",
            postgresql.JSONB,
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "project_id",
            "phase",
            "effective_from",
            name="uq_clearland_phase_project_phase_from",
        ),
    )

    op.create_index(
        "ix_clearland_phase_project_active",
        "clearland_phases",
        ["project_id", "effective_to"],
    )


def downgrade():
    op.drop_index("ix_clearland_phase_project_active", table_name="clearland_phases")
    op.drop_table("clearland_phases")