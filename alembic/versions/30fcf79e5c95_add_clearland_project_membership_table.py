"""add clearland project membership table

Revision ID: 30fcf79e5c95
Revises: f9488f58442a
Create Date: 2026-02-13 01:10:44.315997

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '30fcf79e5c95'
down_revision: Union[str, Sequence[str], None] = 'f9488f58442a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.create_table(
        "clearland_project_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("participant_id", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "enrolled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "project_id",
            "participant_id",
            name="uq_clearland_project_participant",
        ),
    )

    op.create_index(
        "ix_clearland_membership_project",
        "clearland_project_memberships",
        ["project_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_clearland_membership_project",
        table_name="clearland_project_memberships",
    )
    op.drop_table("clearland_project_memberships")