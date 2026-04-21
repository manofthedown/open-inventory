"""Integration tests for the M4 inventory view, export, and casepack flow.

Tests the full HTTP layer for:
- GET /inventory            — on-hand view
- GET /export/items.csv     — items CSV
- GET /export/movements.csv — movements CSV
- Pack alias CRUD (POST /items/{id}/aliases, delete)
- Auto-multiplier scan path (alias GTIN → canonical × multiplier)
"""

from __future__ import annotations

import csv
import io

import respx
from fastapi.testclient import TestClient
from httpx import Response
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from inv.storage.orm import Item as ItemORM


def _item_id_for_gtin(engine: Engine, gtin: str) -> int:
    """Return the database ID for a given GTIN.

    Used instead of assuming ``id=1`` so tests are resilient to
    ordering and fixture changes (issue #19).
    """
    with Session(engine) as sess:
        item = sess.query(ItemORM).filter_by(gtin=gtin).first()
        assert item is not None, f"No item found for GTIN {gtin}"
        return int(item.id)

# ------------------------------------------------------------------ #
# Inventory view                                                      #
# ------------------------------------------------------------------ #


def test_get_inventory_empty(client: TestClient) -> None:
    """GET /inventory renders the page even with no movements."""
    response = client.get("/inventory")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Inventory" in response.text


@respx.mock
def test_get_inventory_shows_scanned_item(client: TestClient) -> None:
    """After a scan, /inventory lists the item with correct on-hand."""
    gtin = "5555555555555"
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{gtin}.json").mock(
        return_value=Response(200, json={"status": 0, "code": gtin})
    )
    client.post("/scan", json={"gtin": gtin, "direction": "IN", "qty_multiplier": 5, "location_id": 1})

    response = client.get("/inventory")
    assert response.status_code == 200
    assert gtin in response.text
    assert "5" in response.text  # on_hand


@respx.mock
def test_get_inventory_hides_zero_stock_items(client: TestClient) -> None:
    """After full depletion, /inventory does not show the item (issue #18)."""
    gtin = "5555555555556"
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{gtin}.json").mock(
        return_value=Response(200, json={"status": 0, "code": gtin})
    )
    client.post("/scan", json={"gtin": gtin, "direction": "IN", "qty_multiplier": 5, "location_id": 1})
    client.post("/scan", json={"gtin": gtin, "direction": "OUT", "qty_multiplier": 5, "location_id": 1})

    response = client.get("/inventory")
    assert response.status_code == 200
    assert gtin not in response.text


# ------------------------------------------------------------------ #
# CSV exports                                                         #
# ------------------------------------------------------------------ #


def test_export_items_csv_empty(client: TestClient) -> None:
    """GET /export/items.csv returns a valid CSV with headers only when empty."""
    response = client.get("/export/items.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers.get("content-disposition", "")

    text = response.content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    assert rows == []
    assert "gtin" in (reader.fieldnames or [])
    assert "on_hand_total" in (reader.fieldnames or [])


@respx.mock
def test_export_items_csv_contains_scanned_item(client: TestClient) -> None:
    """After scanning, items.csv contains the item row with on_hand_total."""
    gtin = "6666666666666"
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{gtin}.json").mock(
        return_value=Response(200, json={"status": 0, "code": gtin})
    )
    client.post("/scan", json={"gtin": gtin, "direction": "IN", "qty_multiplier": 3, "location_id": 1})

    response = client.get("/export/items.csv")
    text = response.content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["gtin"] == gtin
    assert rows[0]["on_hand_total"] == "3"


def test_export_movements_csv_empty(client: TestClient) -> None:
    """GET /export/movements.csv returns valid CSV with headers only when empty."""
    response = client.get("/export/movements.csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]

    text = response.content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)
    assert rows == []
    assert "item_gtin" in (reader.fieldnames or [])
    assert "delta" in (reader.fieldnames or [])


@respx.mock
def test_export_movements_csv_contains_movement(client: TestClient) -> None:
    """After scanning, movements.csv contains the movement row."""
    gtin = "7777777777777"
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{gtin}.json").mock(
        return_value=Response(200, json={"status": 0, "code": gtin})
    )
    client.post("/scan", json={"gtin": gtin, "direction": "IN", "qty_multiplier": 2, "location_id": 1})

    response = client.get("/export/movements.csv")
    text = response.content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["item_gtin"] == gtin
    assert rows[0]["delta"] == "2"
    assert rows[0]["direction"] == "IN"


# ------------------------------------------------------------------ #
# Pack alias CRUD via HTTP                                            #
# ------------------------------------------------------------------ #


@respx.mock
def test_add_and_delete_pack_alias(client: TestClient, engine: Engine) -> None:
    """POST /items/{id}/aliases adds an alias; delete endpoint removes it."""
    canonical_gtin = "8888888888888"
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{canonical_gtin}.json").mock(
        return_value=Response(200, json={"status": 0, "code": canonical_gtin})
    )
    # Create canonical item via scan then resolve its DB id (issue #19)
    client.post("/scan", json={"gtin": canonical_gtin, "direction": "IN", "qty_multiplier": 1, "location_id": 1})
    item_id = _item_id_for_gtin(engine, canonical_gtin)

    # Add alias
    response = client.post(
        f"/items/{item_id}/aliases",
        data={"alias_gtin": "0088888888888", "multiplier": "12", "label": "case-12"},
        follow_redirects=False,
    )
    assert response.status_code == 303

    # Alias should appear on enrich form
    form = client.get(f"/items/{item_id}/enrich")
    assert "0088888888888" in form.text
    assert "case-12" in form.text

    # Delete alias
    del_response = client.post(
        f"/items/{item_id}/aliases/0088888888888/delete",
        follow_redirects=False,
    )
    assert del_response.status_code == 303

    # Alias should be gone
    form_after = client.get(f"/items/{item_id}/enrich")
    assert "0088888888888" not in form_after.text


@respx.mock
def test_add_alias_conflict_with_existing_item(client: TestClient, engine: Engine) -> None:
    """Cannot register an existing item GTIN as an alias (409)."""
    gtin_a = "1000000000001"
    gtin_b = "1000000000002"
    for g in (gtin_a, gtin_b):
        respx.get(f"https://world.openfoodfacts.org/api/v2/product/{g}.json").mock(
            return_value=Response(200, json={"status": 0, "code": g})
        )
    client.post("/scan", json={"gtin": gtin_a, "direction": "IN", "qty_multiplier": 1, "location_id": 1})
    client.post("/scan", json={"gtin": gtin_b, "direction": "IN", "qty_multiplier": 1, "location_id": 1})
    item_a_id = _item_id_for_gtin(engine, gtin_a)

    response = client.post(
        f"/items/{item_a_id}/aliases",
        data={"alias_gtin": gtin_b, "multiplier": "6", "label": ""},
    )
    assert response.status_code == 409


@respx.mock
def test_delete_alias_not_found_returns_404(client: TestClient, engine: Engine) -> None:
    """Deleting a non-existent alias returns 404."""
    gtin = "1000000000003"
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{gtin}.json").mock(
        return_value=Response(200, json={"status": 0, "code": gtin})
    )
    client.post("/scan", json={"gtin": gtin, "direction": "IN", "qty_multiplier": 1, "location_id": 1})
    item_id = _item_id_for_gtin(engine, gtin)

    response = client.post(f"/items/{item_id}/aliases/9999999999999/delete")
    assert response.status_code == 404


# ------------------------------------------------------------------ #
# Auto-multiplier scan path (M4 exit criterion)                      #
# ------------------------------------------------------------------ #


@respx.mock
def test_scan_alias_gtin_applies_auto_multiplier(client: TestClient, engine: Engine) -> None:
    """Scanning a case alias GTIN adds the multiplied eaches in one scan.

    M4 exit criterion: scanning a case barcode for a known alias adds
    the multiplied eaches without operator input.
    """
    canonical_gtin = "2000000000001"
    alias_gtin = "0020000000001"

    # Create canonical item; resolve DB id without assuming it is 1 (issue #19)
    respx.get(f"https://world.openfoodfacts.org/api/v2/product/{canonical_gtin}.json").mock(
        return_value=Response(200, json={"status": 0, "code": canonical_gtin})
    )
    client.post("/scan", json={"gtin": canonical_gtin, "direction": "IN", "qty_multiplier": 1, "location_id": 1})
    item_id = _item_id_for_gtin(engine, canonical_gtin)

    # Register alias (case of 12)
    client.post(
        f"/items/{item_id}/aliases",
        data={"alias_gtin": alias_gtin, "multiplier": "12", "label": "case-12"},
    )

    # Scan the alias GTIN — should add 12 eaches (not 1)
    response = client.post(
        "/scan",
        json={"gtin": alias_gtin, "direction": "IN", "qty_multiplier": 1, "location_id": 1},
    )
    assert response.status_code == 200
    # on_hand should now be 13 (1 initial + 12 from alias scan)
    assert ">13<" in response.text or "13" in response.text
    assert "auto-multiplied" in response.text
