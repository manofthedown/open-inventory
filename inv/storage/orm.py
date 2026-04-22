"""SQLAlchemy 2.x ORM models."""

from datetime import UTC, datetime

from sqlalchemy import JSON, CheckConstraint, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

    pass


class Item(Base):
    """Product item ORM model."""

    __tablename__ = "item"

    id: Mapped[int] = mapped_column(primary_key=True)
    gtin: Mapped[str] = mapped_column(String(14), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(Text)
    brand: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(Text)
    uom: Mapped[str] = mapped_column(String(50), default="each")
    pack_size: Mapped[int] = mapped_column(default=1)
    parent_item_id: Mapped[int | None] = mapped_column(ForeignKey("item.id"))
    meta_data: Mapped[dict | None] = mapped_column(JSON, name="metadata")
    source: Mapped[str | None] = mapped_column(String(100))
    needs_review: Mapped[bool] = mapped_column(default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    # Relationships
    movements: Mapped[list["Movement"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )
    pack_aliases: Mapped[list["PackAlias"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )


class Location(Base):
    """Storage location ORM model."""

    __tablename__ = "location"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text)

    # Relationships
    movements: Mapped[list["Movement"]] = relationship(back_populates="location")


class Movement(Base):
    """Inventory movement (append-only event log) ORM model."""

    __tablename__ = "movement"
    __table_args__ = (
        # Enforce valid direction values at the DB level.
        # Append-only semantics are guaranteed by the application layer:
        # only INSERT is permitted; UPDATE/DELETE are never issued on this table.
        CheckConstraint("direction IN ('IN', 'OUT', 'ADJUST')"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), index=True, nullable=False)
    location_id: Mapped[int] = mapped_column(ForeignKey("location.id"), index=True, nullable=False)
    delta: Mapped[int] = mapped_column(nullable=False)  # Signed quantity in eaches
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # IN, OUT, ADJUST
    actor: Mapped[str | None] = mapped_column(String(255))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), index=True)

    # Relationships
    item: Mapped[Item] = relationship(back_populates="movements")
    location: Mapped[Location] = relationship(back_populates="movements")


class PackAlias(Base):
    """Pack/case alias mapping ORM model."""

    __tablename__ = "pack_alias"

    gtin: Mapped[str] = mapped_column(String(14), primary_key=True, index=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("item.id"), index=True, nullable=False)
    multiplier: Mapped[int] = mapped_column(nullable=False)
    label: Mapped[str | None] = mapped_column(String(100))

    # Relationships
    item: Mapped[Item] = relationship(back_populates="pack_aliases")


class ProductCache(Base):
    """Cached product lookup result ORM model."""

    __tablename__ = "product_cache"

    gtin: Mapped[str] = mapped_column(String(14), primary_key=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC), index=True)
