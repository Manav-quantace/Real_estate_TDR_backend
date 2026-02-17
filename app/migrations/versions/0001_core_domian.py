"""core domain schema: projects, rounds, inventories, charges, participants

Revision ID: 0001_core_domain
Revises:
Create Date: 2025-12-13
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_core_domain"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # projects
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=256), nullable=False),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("zone", sa.String(length=128), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_projects_workflow_city_zone", "projects", ["workflow", "city", "zone"])
    op.create_index("ix_projects_workflow_created_at", "projects", ["workflow", "created_at"])

    # rounds
    op.create_table(
        "rounds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("t", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False, server_default=sa.text("'draft'")),
        sa.Column("bidding_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bidding_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_open", sa.String(length=5), nullable=False, server_default=sa.text("'false'")),
        sa.Column("is_locked", sa.String(length=5), nullable=False, server_default=sa.text("'false'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["workflow", "project_id"],
            ["projects.workflow", "projects.id"],
            name="fk_rounds_project_workflow",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("t >= 0", name="ck_rounds_t_nonnegative"),
        sa.UniqueConstraint("workflow", "project_id", "t", name="uq_rounds_workflow_project_t"),
    )
    op.create_index("ix_rounds_workflow_project_state", "rounds", ["workflow", "project_id", "state"])
    op.create_index("ix_rounds_workflow_project_t", "rounds", ["workflow", "project_id", "t"])

    # unit_inventories
    op.create_table(
        "unit_inventories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("round_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lu", sa.Numeric(20, 4), nullable=True),
        sa.Column("tdru", sa.Numeric(20, 4), nullable=True),
        sa.Column("pru", sa.Numeric(20, 4), nullable=True),
        sa.Column("dcu", sa.Numeric(20, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["workflow", "project_id"],
            ["projects.workflow", "projects.id"],
            name="fk_unit_inventories_project_workflow",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            name="fk_unit_inventories_round",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("workflow", "project_id", "round_id", name="uq_unit_inventory_workflow_project_round"),
        sa.CheckConstraint("lu IS NULL OR lu >= 0", name="ck_unit_inventory_lu_nonneg"),
        sa.CheckConstraint("tdru IS NULL OR tdru >= 0", name="ck_unit_inventory_tdru_nonneg"),
        sa.CheckConstraint("pru IS NULL OR pru >= 0", name="ck_unit_inventory_pru_nonneg"),
        sa.CheckConstraint("dcu IS NULL OR dcu >= 0", name="ck_unit_inventory_dcu_nonneg"),
    )
    op.create_index("ix_unit_inventory_workflow_project_round", "unit_inventories", ["workflow", "project_id", "round_id"])

    # government_charges
    op.create_table(
        "government_charges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("round_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("charge_type", sa.String(length=8), nullable=False),
        sa.Column("weights_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("inputs_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("value_inr", sa.Numeric(20, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["workflow", "project_id"],
            ["projects.workflow", "projects.id"],
            name="fk_government_charges_project_workflow",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["round_id"],
            ["rounds.id"],
            name="fk_government_charges_round",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("workflow", "project_id", "round_id", "charge_type", name="uq_gov_charge_workflow_project_round_type"),
        sa.CheckConstraint("value_inr IS NULL OR value_inr >= 0", name="ck_gov_charge_value_nonneg"),
    )
    op.create_index("ix_gov_charge_workflow_project_round", "government_charges", ["workflow", "project_id", "round_id"])
    op.create_index("ix_gov_charge_type", "government_charges", ["charge_type"])

    # participants
    op.create_table(
        "participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=256), nullable=False),
        sa.Column("profile_json", postgresql.JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("workflow", "id", name="uq_participant_workflow_id"),
    )
    op.create_index("ix_participants_workflow_role", "participants", ["workflow", "role"])


def downgrade():
    op.drop_index("ix_participants_workflow_role", table_name="participants")
    op.drop_table("participants")

    op.drop_index("ix_gov_charge_type", table_name="government_charges")
    op.drop_index("ix_gov_charge_workflow_project_round", table_name="government_charges")
    op.drop_table("government_charges")

    op.drop_index("ix_unit_inventory_workflow_project_round", table_name="unit_inventories")
    op.drop_table("unit_inventories")

    op.drop_index("ix_rounds_workflow_project_t", table_name="rounds")
    op.drop_index("ix_rounds_workflow_project_state", table_name="rounds")
    op.drop_table("rounds")

    op.drop_index("ix_projects_workflow_created_at", table_name="projects")
    op.drop_index("ix_projects_workflow_city_zone", table_name="projects")
    op.drop_table("projects")