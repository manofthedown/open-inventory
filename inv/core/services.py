"""Business logic and service layer.

Services orchestrate repositories, emit events, and enforce domain rules.
All persistence happens inside a single transaction per public service
call so we never leave the DB half-written on errors.
"""

from __future__ import annotations

from typing import Literal, NamedTuple

from sqlalchemy.orm import Session

from inv.core.events import (
    ItemCreatedEvent,
    MovementCreatedEvent,
    item_created,
    movement_created,
)
from inv.storage.orm import Item as ItemORM
from inv.storage.repositories import ItemRepository, LocationRepository, MovementRepository

Direction = Literal["IN", "OUT", "ADJUST"]


class ScanResult(NamedTuple):
    """Result of a scan operation."""

    movement_id: int
    item_id: int
    location_id: int
    item: ItemORM
    on_hand: int
    direction: Direction
    delta: int


class ScanError(Exception):
    """Base exception for scan errors."""


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


def _compute_delta(direction: Direction, qty_multiplier: int) -> int:
    """Turn a (direction, qty_multiplier) pair into a signed delta.

    - IN contributes +qty_multiplier eaches.
    - OUT contributes -qty_multiplier eaches.
    - ADJUST contributes the raw qty_multiplier (may be negative if the
      operator is reconciling a shrink; M2 validates qty_multiplier >= 1
      at the API layer so this currently always yields +qty for ADJUST,
      but the service does not enforce sign so reconciliation tooling
      can land in M3+ without another service-layer change).
    """
    if direction == "IN":
        return qty_multiplier
    if direction == "OUT":
        return -qty_multiplier
    return qty_multiplier


def record_scan(
    session: Session,
    gtin: str,
    direction: Direction,
    qty_multiplier: int = 1,
    location_id: int = 1,
    actor: str | None = None,
    note: str | None = None,
) -> ScanResult:
    """Record a barcode scan and update inventory.

    All writes happen inside a single transaction. Emits
    ``item.created`` (only on first sighting) and ``movement.created``
    (every scan) via :mod:`inv.core.events` after commit.

    Args:
        session: Database session.
        gtin: The barcode (GTIN) scanned. Caller is responsible for
            format validation at the API layer.
        direction: ``"IN"``, ``"OUT"``, or ``"ADJUST"`` — enforced by
            :data:`Direction`.
        qty_multiplier: Number of eaches per scan (1 for each, 12 for a
            case of 12, etc.). API layer validates >= 1.
        location_id: Which location to move stock from/to.
        actor: Who performed the scan (optional).
        note: Additional notes about the movement (optional).

    Returns:
        ScanResult with movement details and current on-hand.

    Raises:
        LocationNotFoundError: If location_id doesn't exist.
        NegativeStockError: If direction is OUT and would drop on-hand
            below 0.
    """
    loc_repo = LocationRepository(session)
    item_repo = ItemRepository(session)
    mov_repo = MovementRepository(session)

    # Validate location exists
    if loc_repo.get_by_id(location_id) is None:
        raise LocationNotFoundError(location_id)

    # Get or create item stub — idempotent, does NOT clobber
    # ``needs_review`` on re-scan (issue #10).
    item, item_was_created = item_repo.get_or_create_stub(gtin)

    # Compute signed delta
    delta = _compute_delta(direction, qty_multiplier)

    # Guard: prevent negative stock on OUT
    if direction == "OUT":
        current = mov_repo.get_on_hand(item.id, location_id)
        if current + delta < 0:
            raise NegativeStockError(gtin, current, abs(delta))

    # Record the movement
    movement = mov_repo.create(
        item_id=item.id,
        location_id=location_id,
        delta=delta,
        direction=direction,
        actor=actor,
        note=note,
    )

    # Single commit covers item stub (if created) + movement.
    session.commit()

    # Re-read on_hand from the view after commit.
    on_hand_after = mov_repo.get_on_hand(item.id, location_id)

    # Emit events AFTER commit so subscribers see a consistent DB state.
    if item_was_created:
        item_created.send(
            "record_scan",
            event=ItemCreatedEvent(item_id=item.id, gtin=item.gtin, source="stub"),
        )

    movement_created.send(
        "record_scan",
        event=MovementCreatedEvent(
            movement_id=movement.id,
            item_id=item.id,
            location_id=location_id,
            delta=delta,
            direction=direction,
            actor=actor,
            created_at=movement.created_at,
        ),
    )

    return ScanResult(
        movement_id=movement.id,
        item_id=item.id,
        location_id=location_id,
        item=item,
        on_hand=on_hand_after,
        direction=direction,
        delta=delta,
    )
