"""round lifecycle constraints: boolean flags + single open round

Revision ID: 0004_rounds_lifecycle_constraints
Revises: 0003_charges_history_and_audit
Create Date: 2025-12-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_rounds_lifecycle_constraints"
down_revision = "0003_charges_history_and_audit"
branch_labels = None
depends_on = None


def upgrade():
    # Convert is_open/is_locked from string -> boolean safely
    op.execute(
        """
        ALTER TABLE rounds
        ALTER COLUMN is_open TYPE boolean
        USING (CASE WHEN is_open IN ('true','True','1') THEN true ELSE false END);
        """
    )
    op.execute(
        """
        ALTER TABLE rounds
        ALTER COLUMN is_locked TYPE boolean
        USING (CASE WHEN is_locked IN ('true','True','1') THEN true ELSE false END);
        """
    )
    op.alter_column("rounds", "is_open", existing_type=sa.Boolean(), nullable=False, server_default=sa.text("false"))
    op.alter_column("rounds", "is_locked", existing_type=sa.Boolean(), nullable=False, server_default=sa.text("false"))

    # Partial unique index: only one open & not locked round per (workflow, project)
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_rounds_single_open
        ON rounds (workflow, project_id)
        WHERE is_open = true AND is_locked = false;
        """
    )

    # State check (structural)
    op.execute(
        """
        ALTER TABLE rounds
        ADD CONSTRAINT ck_rounds_state_valid
        CHECK (state IN ('draft','submitted','locked'));
        """
    )


def downgrade():
    op.execute("ALTER TABLE rounds DROP CONSTRAINT IF EXISTS ck_rounds_state_valid;")
    op.execute("DROP INDEX IF EXISTS uq_rounds_single_open;")

    # Convert back to string (not recommended, but provided)
    op.execute("ALTER TABLE rounds ALTER COLUMN is_open TYPE varchar(5) USING (CASE WHEN is_open THEN 'true' ELSE 'false' END);")
    op.execute("ALTER TABLE rounds ALTER COLUMN is_locked TYPE varchar(5) USING (CASE WHEN is_locked THEN 'true' ELSE 'false' END);")