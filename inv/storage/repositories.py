"""Repository pattern for data access.

Repositories abstract the ORM layer and provide a clean interface for services.
"""

from __future__ import annotations

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

    def create(self, gtin: str, **kwargs) -> Item:  # type: ignore[no-untyped-def]
        """Create a new item."""
        item = Item(gtin=gtin, **kwargs)
        self.session.add(item)
        self.session.commit()
        return item

    def upsert(self, gtin: str, **kwargs) -> Item:  # type: ignore[no-untyped-def]
        """Get or create an item. If it exists, update it."""
        item = self.get_by_gtin(gtin)
        if item:
            for key, value in kwargs.items():
                if value is not None:
                    setattr(item, key, value)
            self.session.commit()
            return item
        return self.create(gtin, **kwargs)


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
        **kwargs: object,
    ) -> Movement:
        """Create a new movement record."""
        movement = Movement(
            item_id=item_id,
            location_id=location_id,
            delta=delta,
            direction=direction,
            **kwargs,
        )
        self.session.add(movement)
        self.session.commit()
        return movement

    def get_on_hand(self, item_id: int, location_id: int) -> int:
        """Get the current on-hand quantity for an item at a location."""
        from sqlalchemy import text

        result = self.session.execute(
            text(
                "SELECT COALESCE(on_hand, 0) FROM inventory_view "
                "WHERE item_id = :item_id AND location_id = :location_id"
            ),
            {"item_id": item_id, "location_id": location_id},
        ).scalar()
        return int(result) if result is not None else 0
