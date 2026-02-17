"""add slum consents and documents

Revision ID: 53e8e84312de
Revises: 1955168c8cb4
Create Date: 2026-01-29 14:04:37.780758

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '53e8e84312de'
down_revision: Union[str, Sequence[str], None] = '1955168c8cb4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
