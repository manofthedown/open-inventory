"""Unit tests for scan services."""

from __future__ import annotations

import pytest

from inv.core.services import (
    LocationNotFoundError,
    NegativeStockError,
    record_scan,
)


def test_record_scan_creates_stub_for_unknown_gtin(session, settings) -> None:
    """record_scan creates a stub item for unknown GTINs."""
    gtin = "9999999999999"
    result = record_scan(session, gtin=gtin, direction="IN", qty_multiplier=1, location_id=1)

    assert result.item.gtin == gtin
    assert result.on_hand == 1
    assert result.delta == 1
    assert result.direction == "IN"


def test_record_scan_increments_on_hand_for_in(session) -> None:
    """record_scan with direction=IN increments on_hand."""
    gtin = "1111111111111"

    # Scan in 5
    r1 = record_scan(session, gtin=gtin, direction="IN", qty_multiplier=5, location_id=1)
    assert r1.on_hand == 5

    # Scan in 3 more
    r2 = record_scan(session, gtin=gtin, direction="IN", qty_multiplier=3, location_id=1)
    assert r2.on_hand == 8


def test_record_scan_decrements_on_hand_for_out(session) -> None:
    """record_scan with direction=OUT decrements on_hand."""
    gtin = "2222222222222"

    # Scan in 10
    record_scan(session, gtin=gtin, direction="IN", qty_multiplier=10, location_id=1)

    # Scan out 3
    result = record_scan(session, gtin=gtin, direction="OUT", qty_multiplier=3, location_id=1)
    assert result.on_hand == 7


def test_record_scan_rejects_negative_stock(session) -> None:
    """record_scan with direction=OUT raises NegativeStockError if would drop below 0."""
    gtin = "3333333333333"

    # Scan in 5
    record_scan(session, gtin=gtin, direction="IN", qty_multiplier=5, location_id=1)

    # Try to scan out 10
    with pytest.raises(NegativeStockError):
        record_scan(session, gtin=gtin, direction="OUT", qty_multiplier=10, location_id=1)


def test_record_scan_rejects_unknown_location(session) -> None:
    """record_scan with unknown location_id raises LocationNotFoundError."""
    with pytest.raises(LocationNotFoundError):
        record_scan(
            session,
            gtin="4444444444444",
            direction="IN",
            qty_multiplier=1,
            location_id=999,
        )


def test_record_scan_respects_qty_multiplier(session) -> None:
    """qty_multiplier is applied correctly (e.g., case = 12 units)."""
    gtin = "5555555555555"

    # Scan a case (multiplier=12)
    result = record_scan(session, gtin=gtin, direction="IN", qty_multiplier=12, location_id=1)
    assert result.on_hand == 12
    assert result.delta == 12


def test_record_scan_adjust_direction(session) -> None:
    """direction=ADJUST adds the delta without negative stock guards."""
    gtin = "6666666666666"

    # Scan in 10
    record_scan(session, gtin=gtin, direction="IN", qty_multiplier=10, location_id=1)

    # Adjust by +5 (no negative stock guard on ADJUST)
    result = record_scan(session, gtin=gtin, direction="ADJUST", qty_multiplier=5, location_id=1)
    assert result.on_hand == 15
    assert result.direction == "ADJUST"


def test_record_scan_does_not_clobber_needs_review_on_rescan(session) -> None:
    """Re-scanning a known GTIN must NOT reset the ``needs_review`` flag.

    Regression for issue #10: the old ``upsert(**kwargs)`` path passed
    ``needs_review=False`` on every re-scan and blindly overwrote the
    column, breaking M3's manual-enrichment queue.
    """
    gtin = "7777777777777"

    # First scan — creates a stub with needs_review=True
    r1 = record_scan(session, gtin=gtin, direction="IN", qty_multiplier=1, location_id=1)
    assert r1.item.needs_review is True

    # Second scan — the flag must remain True (no human has enriched yet)
    r2 = record_scan(session, gtin=gtin, direction="IN", qty_multiplier=1, location_id=1)
    assert r2.item.needs_review is True

    # Simulate an operator enriching the item (clearing the flag)
    r2.item.needs_review = False
    session.commit()

    # Third scan — the flag stays cleared (record_scan must not re-set it)
    r3 = record_scan(session, gtin=gtin, direction="IN", qty_multiplier=1, location_id=1)
    assert r3.item.needs_review is False


def test_record_scan_emits_movement_created_signal(session) -> None:
    """Every ``record_scan`` fires ``movement.created`` with the correct payload."""
    from inv.core.events import MovementCreatedEvent, movement_created

    received: list[MovementCreatedEvent] = []

    def _catch(_sender: object, event: MovementCreatedEvent) -> None:
        received.append(event)

    movement_created.connect(_catch)
    try:
        result = record_scan(
            session, gtin="8888888888888", direction="IN", qty_multiplier=3, location_id=1
        )
    finally:
        movement_created.disconnect(_catch)

    assert len(received) == 1
    evt = received[0]
    assert evt.movement_id == result.movement_id
    assert evt.item_id == result.item_id
    assert evt.location_id == 1
    assert evt.delta == 3
    assert evt.direction == "IN"


def test_record_scan_emits_item_created_only_once(session) -> None:
    """``item.created`` fires on the first scan only; re-scans are silent."""
    from inv.core.events import ItemCreatedEvent, item_created

    received: list[ItemCreatedEvent] = []

    def _catch(_sender: object, event: ItemCreatedEvent) -> None:
        received.append(event)

    gtin = "9000000000009"
    item_created.connect(_catch)
    try:
        record_scan(session, gtin=gtin, direction="IN", qty_multiplier=1, location_id=1)
        record_scan(session, gtin=gtin, direction="IN", qty_multiplier=1, location_id=1)
        record_scan(session, gtin=gtin, direction="IN", qty_multiplier=1, location_id=1)
    finally:
        item_created.disconnect(_catch)

    assert len(received) == 1
    assert received[0].gtin == gtin
    assert received[0].source == "stub"
