"""Initial schema creation

Revision ID: 0001
Revises:
Create Date: 2025-04-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial tables."""
    # item table
    op.create_table(
        "item",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gtin", sa.String(length=14), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("brand", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("uom", sa.String(length=50), nullable=False, server_default="each"),
        sa.Column("pack_size", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("parent_item_id", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("needs_review", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_item_id"], ["item.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("gtin"),
    )
    op.create_index(op.f("ix_item_gtin"), "item", ["gtin"], unique=True)
    op.create_index(op.f("ix_item_needs_review"), "item", ["needs_review"], unique=False)

    # location table
    op.create_table(
        "location",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_location_name"), "location", ["name"], unique=True)

    # movement table
    op.create_table(
        "movement",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("direction", sa.String(length=10), nullable=False),
        sa.Column("actor", sa.String(length=255), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("direction IN ('IN', 'OUT', 'ADJUST')", name="check_direction"),
        sa.ForeignKeyConstraint(["item_id"], ["item.id"], ),
        sa.ForeignKeyConstraint(["location_id"], ["location.id"], ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id"),
    )
    op.create_index(op.f("ix_movement_created_at"), "movement", ["created_at"], unique=False)
    op.create_index(op.f("ix_movement_item_id"), "movement", ["item_id"], unique=False)
    op.create_index(op.f("ix_movement_location_id"), "movement", ["location_id"], unique=False)

    # pack_alias table
    op.create_table(
        "pack_alias",
        sa.Column("gtin", sa.String(length=14), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False),
        sa.Column("multiplier", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["item_id"], ["item.id"], ),
        sa.PrimaryKeyConstraint("gtin"),
    )
    op.create_index(op.f("ix_pack_alias_gtin"), "pack_alias", ["gtin"], unique=True)
    op.create_index(op.f("ix_pack_alias_item_id"), "pack_alias", ["item_id"], unique=False)

    # product_cache table
    op.create_table(
        "product_cache",
        sa.Column("gtin", sa.String(length=14), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("gtin"),
    )
    op.create_index(op.f("ix_product_cache_fetched_at"), "product_cache", ["fetched_at"], unique=False)
    op.create_index(op.f("ix_product_cache_gtin"), "product_cache", ["gtin"], unique=True)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index(op.f("ix_product_cache_gtin"), table_name="product_cache")
    op.drop_index(op.f("ix_product_cache_fetched_at"), table_name="product_cache")
    op.drop_table("product_cache")
    op.drop_index(op.f("ix_pack_alias_item_id"), table_name="pack_alias")
    op.drop_index(op.f("ix_pack_alias_gtin"), table_name="pack_alias")
    op.drop_table("pack_alias")
    op.drop_index(op.f("ix_movement_location_id"), table_name="movement")
    op.drop_index(op.f("ix_movement_item_id"), table_name="movement")
    op.drop_index(op.f("ix_movement_created_at"), table_name="movement")
    op.drop_table("movement")
    op.drop_index(op.f("ix_location_name"), table_name="location")
    op.drop_table("location")
    op.drop_index(op.f("ix_item_needs_review"), table_name="item")
    op.drop_index(op.f("ix_item_gtin"), table_name="item")
    op.drop_table("item")
