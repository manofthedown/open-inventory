"""Repository pattern for data access.

Repositories wrap the ORM and expose intent-revealing methods to the
service layer. No business logic lives here — just CRUD and read models.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from inv.storage.orm import Item, Location, Movement


class ItemRepository:
    """Repository for Item operations."""

    def __init__(self, session: Session) -> None:
        """Initialize with a database session."""
        self.session = session

    def get_by_gtin(self, gtin: str) -> Item | None:
        """Get an item by GTIN, or None if not found."""
        return self.session.query(Item).filter_by(gtin=gtin).first()

    def get_by_id(self, item_id: int) -> Item | None:
        """Get an item by ID."""
        return self.session.query(Item).filter_by(id=item_id).first()

    def create(self, gtin: str, **fields: Any) -> Item:
        """Create a new item. Caller is responsible for flushing/committing."""
        item = Item(gtin=gtin, **fields)
        self.session.add(item)
        self.session.flush()
        return item

    def get_or_create_stub(self, gtin: str) -> tuple[Item, bool]:
        """Return (item, created) — idempotent by GTIN.

        If the item already exists, return it unchanged (never touches
        ``needs_review`` or any other field). If it doesn't exist,
        create a ``needs_review=True`` stub.

        This explicit shape replaces the old ``upsert(**kwargs)`` which
        clobbered ``needs_review`` on every re-scan (see issue #10).
        """
        existing = self.get_by_gtin(gtin)
        if existing is not None:
            return existing, False
        return self.create(gtin, needs_review=True, source="stub"), True

    def update_fields(self, item: Item, **fields: Any) -> Item:
        """Update one or more fields on an existing item.

        Only writes fields that were explicitly passed. Used by M3's
        enrichment flow; M2 does not call this from the scan path.
        """
        for key, value in fields.items():
            setattr(item, key, value)
        self.session.flush()
        return item


class LocationRepository:
    """Repository for Location operations."""

    def __init__(self, session: Session) -> None:
        """Initialize with a database session."""
        self.session = session

    def get_by_id(self, location_id: int) -> Location | None:
        """Get a location by ID."""
        return self.session.query(Location).filter_by(id=location_id).first()

    def get_by_name(self, name: str) -> Location | None:
        """Get a location by name."""
        return self.session.query(Location).filter_by(name=name).first()

    def list_all(self) -> list[Location]:
        """Get all locations."""
        return self.session.query(Location).all()


class MovementRepository:
    """Repository for Movement operations."""

    def __init__(self, session: Session) -> None:
        """Initialize with a database session."""
        self.session = session

    def create(
        self,
        item_id: int,
        location_id: int,
        delta: int,
        direction: str,
        actor: str | None = None,
        note: str | None = None,
    ) -> Movement:
        """Create a new movement row. Caller owns the commit."""
        movement = Movement(
            item_id=item_id,
            location_id=location_id,
            delta=delta,
            direction=direction,
            actor=actor,
            note=note,
        )
        self.session.add(movement)
        self.session.flush()
        return movement

    def get_on_hand(self, item_id: int, location_id: int) -> int:
        """Get the current on-hand quantity for an item at a location.

        Reads from the ``inventory_view`` SQL VIEW created by the baseline
        migration. Returns 0 if no movements exist.
        """
        result = self.session.execute(
            text(
                "SELECT COALESCE(on_hand, 0) FROM inventory_view "
                "WHERE item_id = :item_id AND location_id = :location_id"
            ),
            {"item_id": item_id, "location_id": location_id},
        ).scalar()
        return int(result) if result is not None else 0
