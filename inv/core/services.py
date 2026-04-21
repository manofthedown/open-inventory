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
    ItemEnrichedEvent,
    MovementCreatedEvent,
    ScanUnknownEvent,
    item_created,
    item_enriched,
    movement_created,
    scan_unknown,
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
    lookup_result: object | None = None,
) -> ScanResult:
    """Record a barcode scan and update inventory.

    All writes happen inside a single transaction. Emits
    ``item.created`` (only on first sighting), ``movement.created``
    (every scan), and ``scan.unknown`` (when no lookup result was found
    for a newly created item) via :mod:`inv.core.events` after commit.

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
        lookup_result: A ``ProviderResult`` returned by ``ChainRunner``
            (or ``None`` if the chain missed). When provided for a
            newly-created item the fields are applied immediately so the
            item is enriched in the same transaction as the movement.
            Pass ``None`` to leave the item as a plain stub.

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

    # If we have a fresh lookup result for a new item, apply it now so
    # the item is enriched in the same transaction as the movement.
    # Only touch fields on creation — never overwrite on re-scan.
    if item_was_created and lookup_result is not None:
        # lookup_result is a ProviderResult; import here to avoid a
        # circular import between core.services and inv.lookup.
        from inv.lookup.base import ProviderResult

        if isinstance(lookup_result, ProviderResult):
            fields: dict[str, object] = {"source": lookup_result.provider}
            if lookup_result.name is not None:
                fields["name"] = lookup_result.name
            if lookup_result.brand is not None:
                fields["brand"] = lookup_result.brand
            if lookup_result.category is not None:
                fields["category"] = lookup_result.category
            # Clear needs_review since we have real data
            fields["needs_review"] = False
            item_repo.update_fields(item, **fields)

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

    # Single commit covers item stub (if created) + enrichment + movement.
    session.commit()

    # Re-read on_hand from the view after commit.
    on_hand_after = mov_repo.get_on_hand(item.id, location_id)

    # Emit events AFTER commit so subscribers see a consistent DB state.
    if item_was_created:
        item_created.send(
            "record_scan",
            event=ItemCreatedEvent(
                item_id=item.id,
                gtin=item.gtin,
                source=item.source or "stub",
            ),
        )
        if lookup_result is None:
            # All providers missed — flag it for manual enrichment.
            scan_unknown.send(
                "record_scan",
                event=ScanUnknownEvent(
                    gtin=gtin,
                    attempted_providers=(),
                ),
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


def enrich_item(
    session: Session,
    item_id: int,
    name: str | None = None,
    brand: str | None = None,
    category: str | None = None,
    note: str | None = None,
) -> ItemORM:
    """Manually enrich an item and clear its ``needs_review`` flag.

    Used by the ``POST /items/{id}/enrich`` route. Only updates fields
    that are explicitly provided (non-None). Always clears ``needs_review``
    after a successful enrichment.

    Emits ``item.enriched`` after commit.

    Raises:
        KeyError: If no item with ``item_id`` exists.
    """
    item_repo = ItemRepository(session)
    item = item_repo.get_by_id(item_id)
    if item is None:
        raise KeyError(f"Item {item_id} not found")

    fields: dict[str, object] = {"needs_review": False, "source": "manual"}
    filled: list[str] = []
    if name is not None:
        fields["name"] = name
        filled.append("name")
    if brand is not None:
        fields["brand"] = brand
        filled.append("brand")
    if category is not None:
        fields["category"] = category
        filled.append("category")
    if note is not None:
        fields["meta_data"] = {**(item.meta_data or {}), "enrich_note": note}
        filled.append("note")

    item_repo.update_fields(item, **fields)
    session.commit()

    item_enriched.send(
        "enrich_item",
        event=ItemEnrichedEvent(
            item_id=item.id,
            provider="manual",
            fields_filled=tuple(filled),
        ),
    )

    return item
