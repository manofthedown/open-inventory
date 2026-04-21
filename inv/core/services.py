"""Business logic and service layer.

Services orchestrate repositories, emit events, and enforce domain rules.
"""

from __future__ import annotations

from typing import NamedTuple

from sqlalchemy.orm import Session

from inv.storage.orm import Item as ItemORM
from inv.storage.repositories import ItemRepository, LocationRepository, MovementRepository


class ScanResult(NamedTuple):
    """Result of a scan operation."""

    movement_id: int
    item_id: int
    location_id: int
    item: ItemORM
    on_hand: int
    direction: str
    delta: int


class ScanError(Exception):
    """Base exception for scan errors."""

    pass


class NegativeStockError(ScanError):
    """Raised when attempting to scan out more than is on hand."""

    def __init__(self, item_gtin: str, on_hand: int, requested_delta: int) -> None:
        """Initialize with details about the stock error."""
        self.item_gtin = item_gtin
        self.on_hand = on_hand
        self.requested_delta = requested_delta
        super().__init__(
            f"Cannot remove {requested_delta} units of {item_gtin}; only {on_hand} on hand"
        )


class LocationNotFoundError(ScanError):
    """Raised when a location doesn't exist."""

    def __init__(self, location_id: int) -> None:
        """Initialize with the missing location ID."""
        self.location_id = location_id
        super().__init__(f"Location {location_id} not found")


def record_scan(
    session: Session,
    gtin: str,
    direction: str,
    qty_multiplier: int = 1,
    location_id: int = 1,
    actor: str | None = None,
    note: str | None = None,
) -> ScanResult:
    """Record a barcode scan and update inventory.

    Args:
        session: Database session.
        gtin: The barcode (GTIN) scanned.
        direction: 'IN', 'OUT', or 'ADJUST'.
        qty_multiplier: Number of eaches per scan (1 for each, 12 for case, etc).
        location_id: Which location to move stock from/to.
        actor: Who performed the scan (optional).
        note: Additional notes about the movement (optional).

    Returns:
        ScanResult with movement details and current on-hand.

    Raises:
        LocationNotFoundError: If location_id doesn't exist.
        NegativeStockError: If direction is OUT and would drop on-hand below 0.
    """
    # Validate location exists
    loc_repo = LocationRepository(session)
    location = loc_repo.get_by_id(location_id)
    if not location:
        raise LocationNotFoundError(location_id)

    # Get or create item (stub if unknown)
    item_repo = ItemRepository(session)
    item = item_repo.upsert(gtin, needs_review=(True if not item_repo.get_by_gtin(gtin) else False))

    # Calculate delta
    mov_repo = MovementRepository(session)
    delta = (
        qty_multiplier
        if direction == "IN"
        else -qty_multiplier
        if direction == "OUT"
        else qty_multiplier
    )

    # Guard: prevent negative stock on OUT
    if direction == "OUT":
        on_hand = mov_repo.get_on_hand(item.id, location_id)
        if on_hand + delta < 0:
            raise NegativeStockError(gtin, on_hand, abs(delta))

    # Record the movement
    movement = mov_repo.create(
        item_id=item.id,
        location_id=location_id,
        delta=delta,
        direction=direction,
        actor=actor,
        note=note,
    )

    # Fetch new on-hand
    on_hand_after = mov_repo.get_on_hand(item.id, location_id)

    return ScanResult(
        movement_id=movement.id,
        item_id=item.id,
        location_id=location_id,
        item=item,
        on_hand=on_hand_after,
        direction=direction,
        delta=delta,
    )
