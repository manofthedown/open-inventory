"""Integration tests for the M3 enrichment flow.

Tests the full HTTP layer for:
- GET /items          — item list with needs_review filter
- GET /items/{id}/enrich  — enrichment form render
- POST /items/{id}/enrich — form submission + redirect
- POST /scan with lookup chain mocked — enrichment in-scan-path
- scan.unknown signal fired when all providers miss
"""

from __future__ import annotations

import json
from pathlib import Path

import respx
from fastapi.testclient import TestClient
from httpx import Response


# ------------------------------------------------------------------ #
# Item list                                                           #
# ------------------------------------------------------------------ #


def test_get_items_empty_list(client: TestClient) -> None:
    """GET /items renders the list page even when no items exist."""
    response = client.get("/items")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@respx.mock
def test_get_items_needs_review_filter(client: TestClient) -> None:
    """GET /items?filter=needs_review shows items flagged for review.

    Uses a GTIN that misses every provider so the stub stays needs_review=True.
    """
    gtin = "0000000000001"
    # OFF misses
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{gtin}.json").mock(
        return_value=Response(200, json={"status": 0, "code": gtin})
    )
    client.post(
        "/scan",
        json={"gtin": gtin, "direction": "IN", "qty_multiplier": 1, "location_id": 1},
    )
    response = client.get("/items?filter=needs_review")
    assert response.status_code == 200
    assert "needs review" in response.text


# ------------------------------------------------------------------ #
# Enrichment form                                                     #
# ------------------------------------------------------------------ #


def test_get_enrich_form_for_existing_item(client: TestClient) -> None:
    """GET /items/{id}/enrich renders the form for an existing item."""
    # Create an item via scan
    client.post(
        "/scan",
        json={"gtin": "1111111111111", "direction": "IN", "qty_multiplier": 1, "location_id": 1},
    )
    # Item should be id=1 in a fresh DB
    response = client.get("/items/1/enrich")
    assert response.status_code == 200
    assert "Enrich item" in response.text
    assert "1111111111111" in response.text


def test_get_enrich_form_unknown_id_returns_404(client: TestClient) -> None:
    """GET /items/9999/enrich returns 404 for a non-existent item."""
    response = client.get("/items/9999/enrich")
    assert response.status_code == 404


def test_post_enrich_form_clears_needs_review(client: TestClient) -> None:
    """POST /items/{id}/enrich clears needs_review and redirects to /items."""
    # Create a stub item
    client.post(
        "/scan",
        json={"gtin": "2222222222222", "direction": "IN", "qty_multiplier": 1, "location_id": 1},
    )

    response = client.post(
        "/items/1/enrich",
        data={"name": "Test Product", "brand": "Test Brand", "category": "Food", "note": ""},
        follow_redirects=False,
    )
    # Should redirect to /items (303)
    assert response.status_code == 303
    assert response.headers["location"] == "/items"

    # Follow redirect and verify the item no longer shows needs_review
    items_page = client.get("/items")
    assert "Test Product" in items_page.text


def test_post_enrich_form_unknown_id_returns_404(client: TestClient) -> None:
    """POST /items/9999/enrich returns 404."""
    response = client.post(
        "/items/9999/enrich",
        data={"name": "X", "brand": "", "category": "", "note": ""},
    )
    assert response.status_code == 404


# ------------------------------------------------------------------ #
# Scan path with lookup chain                                         #
# ------------------------------------------------------------------ #


@respx.mock
def test_scan_unknown_gtin_enriched_from_off(
    client: TestClient, provider_fixtures_dir: Path
) -> None:
    """First scan of a food GTIN populates name/brand from Open Food Facts."""
    gtin = "3017620422003"
    payload = json.loads((provider_fixtures_dir / "openfoodfacts_hit.json").read_text())
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{gtin}.json").mock(
        return_value=Response(200, json=payload)
    )

    response = client.post(
        "/scan",
        json={"gtin": gtin, "direction": "IN", "qty_multiplier": 1, "location_id": 1},
    )
    assert response.status_code == 200
    # The partial should show the product name, not the raw GTIN
    assert "Nutella" in response.text


@respx.mock
def test_scan_isbn_enriched_from_openlibrary(
    client: TestClient, provider_fixtures_dir: Path
) -> None:
    """First scan of an ISBN-13 populates title/author from Open Library."""
    isbn = "9780140328721"
    # OFF will miss (not an ISBN in their DB — simulate miss)
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{isbn}.json").mock(
        return_value=Response(200, json={"status": 0, "code": isbn})
    )
    # Open Library hit
    payload = json.loads((provider_fixtures_dir / "openlibrary_hit.json").read_text())
    respx.get("https://openlibrary.org/api/books").mock(
        return_value=Response(200, json=payload)
    )

    response = client.post(
        "/scan",
        json={"gtin": isbn, "direction": "IN", "qty_multiplier": 1, "location_id": 1},
    )
    assert response.status_code == 200
    assert "Fantastic Mr. Fox" in response.text


@respx.mock
def test_scan_all_providers_miss_creates_needs_review_stub(client: TestClient) -> None:
    """When all providers miss, the item is created with needs_review=True."""
    gtin = "0000000000000"
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{gtin}.json").mock(
        return_value=Response(200, json={"status": 0, "code": gtin})
    )
    # Open Library skipped (not an ISBN)
    # OpenGTINdb always misses
    # UPCitemdb: 13-digit not zero-prefixed → skipped

    response = client.post(
        "/scan",
        json={"gtin": gtin, "direction": "IN", "qty_multiplier": 1, "location_id": 1},
    )
    assert response.status_code == 200

    # The item should appear in the needs_review filter
    items_page = client.get("/items?filter=needs_review")
    assert gtin in items_page.text


@respx.mock
def test_rescan_known_gtin_skips_chain(
    client: TestClient, provider_fixtures_dir: Path
) -> None:
    """Re-scanning a known GTIN does not hit the network (chain is bypassed)."""
    gtin = "3017620422003"
    payload = json.loads((provider_fixtures_dir / "openfoodfacts_hit.json").read_text())

    # First scan — chain runs
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{gtin}.json").mock(
        return_value=Response(200, json=payload)
    )
    client.post(
        "/scan",
        json={"gtin": gtin, "direction": "IN", "qty_multiplier": 1, "location_id": 1},
    )

    # Second scan — no route registered; respx will raise if network is hit
    with respx.mock:
        response = client.post(
            "/scan",
            json={"gtin": gtin, "direction": "IN", "qty_multiplier": 1, "location_id": 1},
        )
    assert response.status_code == 200


# ------------------------------------------------------------------ #
# scan.unknown signal                                                 #
# ------------------------------------------------------------------ #


@respx.mock
def test_scan_unknown_signal_fired_on_all_miss(client: TestClient) -> None:
    """scan.unknown is fired exactly once when all providers miss a new GTIN."""
    from inv.core.events import ScanUnknownEvent, scan_unknown

    received: list[ScanUnknownEvent] = []

    def _catch(_sender: object, event: ScanUnknownEvent) -> None:
        received.append(event)

    gtin = "1000000000000"
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{gtin}.json").mock(
        return_value=Response(200, json={"status": 0, "code": gtin})
    )

    scan_unknown.connect(_catch)
    try:
        client.post(
            "/scan",
            json={"gtin": gtin, "direction": "IN", "qty_multiplier": 1, "location_id": 1},
        )
    finally:
        scan_unknown.disconnect(_catch)

    assert len(received) == 1
    assert received[0].gtin == gtin
    # attempted_providers must now be populated — not an empty tuple (issue #22)
    assert len(received[0].attempted_providers) > 0
    assert "openfoodfacts" in received[0].attempted_providers
