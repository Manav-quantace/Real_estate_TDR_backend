"""ask bid separate columns for DCU + compensatory + delta

Revision ID: 0006_ask_bid_columns_dcu_comp_delta
Revises: 0005_bid_tables_and_immutability
Create Date: 2025-12-14
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_ask_bid_columns_dcu_comp_delta"
down_revision = "0005_bid_tables_and_immutability"
branch_labels = None
depends_on = None


def upgrade():
    # numeric columns (INR money stored as numeric(20,2), units as numeric(20,4))
    op.add_column("ask_bids", sa.Column("dcu_units", sa.Numeric(20, 4), nullable=True))
    op.add_column("ask_bids", sa.Column("ask_price_per_unit_inr", sa.Numeric(20, 2), nullable=True))
    op.add_column("ask_bids", sa.Column("total_ask_inr", sa.Numeric(20, 2), nullable=True))

    op.add_column("ask_bids", sa.Column("comp_dcu_units", sa.Numeric(20, 4), nullable=True))
    op.add_column("ask_bids", sa.Column("comp_ask_price_per_unit_inr", sa.Numeric(20, 2), nullable=True))

    op.add_column("ask_bids", sa.Column("delta_ask_next_round_inr", sa.Numeric(20, 2), nullable=True))

    op.create_index("ix_ask_bids_dcu_cols", "ask_bids", ["workflow", "project_id", "t"])


def downgrade():
    op.drop_index("ix_ask_bids_dcu_cols", table_name="ask_bids")

    op.drop_column("ask_bids", "delta_ask_next_round_inr")
    op.drop_column("ask_bids", "comp_ask_price_per_unit_inr")
    op.drop_column("ask_bids", "comp_dcu_units")

    op.drop_column("ask_bids", "total_ask_inr")
    op.drop_column("ask_bids", "ask_price_per_unit_inr")
    op.drop_column("ask_bids", "dcu_units")