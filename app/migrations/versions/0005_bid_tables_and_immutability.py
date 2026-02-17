"""bid tables + immutability triggers

Revision ID: 0005_bid_tables_and_immutability
Revises: 0004_rounds_lifecycle_constraints
Create Date: 2025-12-14
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_bid_tables_and_immutability"
down_revision = "0004_rounds_lifecycle_constraints"
branch_labels = None
depends_on = None


def upgrade():
    # Quote bids
    op.create_table(
        "quote_bids",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("round_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("t", sa.Integer(), nullable=False),
        sa.Column("participant_id", sa.String(length=128), nullable=False),
        sa.Column(
            "state",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column(
            "payload_json",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("signature_hash", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "workflow", "project_id", "t", "participant_id", name="uq_quote_bid_scope"
        ),
    )
    op.create_index(
        "ix_quote_bid_lookup", "quote_bids", ["workflow", "project_id", "t"]
    )
    op.create_index("ix_quote_bid_round", "quote_bids", ["round_id"])

    # Ask bids
    op.create_table(
        "ask_bids",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("round_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("t", sa.Integer(), nullable=False),
        sa.Column("participant_id", sa.String(length=128), nullable=False),
        sa.Column(
            "state",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column(
            "payload_json",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("signature_hash", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "workflow", "project_id", "t", "participant_id", name="uq_ask_bid_scope"
        ),
    )
    op.create_index("ix_ask_bid_lookup", "ask_bids", ["workflow", "project_id", "t"])
    op.create_index("ix_ask_bid_round", "ask_bids", ["round_id"])

    # Preference bids
    op.create_table(
        "preference_bids",
        sa.Column(
            "id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False
        ),
        sa.Column("workflow", sa.String(length=32), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("round_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("t", sa.Integer(), nullable=False),
        sa.Column("participant_id", sa.String(length=128), nullable=False),
        sa.Column(
            "state",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        sa.Column(
            "payload_json",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("signature_hash", sa.String(length=128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["round_id"], ["rounds.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "workflow",
            "project_id",
            "t",
            "participant_id",
            name="uq_preference_bid_scope",
        ),
    )
    op.create_index(
        "ix_preference_bid_lookup", "preference_bids", ["workflow", "project_id", "t"]
    )
    op.create_index("ix_preference_bid_round", "preference_bids", ["round_id"])

    # --- DB-level immutability: reject UPDATE if state='locked' ---
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_update_locked_bids()
        RETURNS trigger AS $$
        BEGIN
            IF OLD.state = 'locked' THEN
                RAISE EXCEPTION 'Locked bids are immutable (append-only).';
            END IF;
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    for table in ("quote_bids", "ask_bids", "preference_bids"):
        op.execute(
            f"""
            DROP TRIGGER IF EXISTS trg_prevent_update_locked_{table} ON {table};
            CREATE TRIGGER trg_prevent_update_locked_{table}
            BEFORE UPDATE ON {table}
            FOR EACH ROW
            EXECUTE FUNCTION prevent_update_locked_bids();
            """
        )


def downgrade():
    for table in ("quote_bids", "ask_bids", "preference_bids"):
        op.execute(
            f"DROP TRIGGER IF EXISTS trg_prevent_update_locked_{table} ON {table};"
        )

    op.execute("DROP FUNCTION IF EXISTS prevent_update_locked_bids();")

    op.drop_index("ix_preference_bid_round", table_name="preference_bids")
    op.drop_index("ix_preference_bid_lookup", table_name="preference_bids")
    op.drop_table("preference_bids")

    op.drop_index("ix_ask_bid_round", table_name="ask_bids")
    op.drop_index("ix_ask_bid_lookup", table_name="ask_bids")
    op.drop_table("ask_bids")

    op.drop_index("ix_quote_bid_round", table_name="quote_bids")
    op.drop_index("ix_quote_bid_lookup", table_name="quote_bids")
    op.drop_table("quote_bids")
