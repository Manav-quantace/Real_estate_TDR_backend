"""add subsidized economic model table

Revision ID: 1ba313f548dc
Revises: 7e695d4aa2c5
Create Date: 2026-02-04 13:10:55.493435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa



# revision identifiers, used by Alembic.
revision: str = '1ba313f548dc'
down_revision: Union[str, Sequence[str], None] = '7e695d4aa2c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        "subsidized_economic_models",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", sa.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("is_published_version", sa.Boolean(), server_default=sa.text("false"), nullable=False),

        sa.Column("lu_total", sa.Integer(), nullable=False),
        sa.Column("lu_open_space", sa.Integer(), nullable=False),
        sa.Column("pru_total", sa.Integer(), nullable=True),
        sa.Column("tdru_total", sa.Integer(), nullable=True),
        sa.Column("dcu_total", sa.Integer(), nullable=True),

        sa.Column("pvic", sa.Numeric(20, 2), nullable=True),

        sa.Column("alpha", sa.Numeric(10, 6), nullable=True),
        sa.Column("beta", sa.Numeric(10, 6), nullable=True),
        sa.Column("gamma", sa.Numeric(10, 6), nullable=True),

        sa.Column("ec", sa.Numeric(20, 2), nullable=True),
        sa.Column("gci", sa.Numeric(20, 2), nullable=True),
        sa.Column("gce", sa.Numeric(20, 2), nullable=True),
        sa.Column("gcu", sa.Numeric(20, 2), nullable=True),

        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("computed_at", sa.DateTime(timezone=True), nullable=True),

        sa.UniqueConstraint("project_id", "version", name="uq_subsidized_model_proj_ver"),
    )
    op.create_index("ix_subsidized_model_proj", "subsidized_economic_models", ["project_id"])


def downgrade():
    op.drop_index("ix_subsidized_model_proj", table_name="subsidized_economic_models")
    op.drop_table("subsidized_economic_models")
