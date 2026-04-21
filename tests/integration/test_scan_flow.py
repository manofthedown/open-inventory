"""HTTP-level tests for the scan loop (M2).

Covers the ``GET /scan`` page render and the ``POST /scan`` request
contract — including every branch of the M2 exit criteria and every
validation rule on :class:`inv.api.routes_scan.ScanRequest`.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------- #
# GET /scan                                                              #
# ---------------------------------------------------------------------- #


def test_get_scan_page_renders_mode_selector(client: TestClient) -> None:
    """GET /scan returns the scan UI with every required control."""
    response = client.get("/scan")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")

    body = response.text
    # Mode selector values (Each, Case, Cluster, Custom)
    assert 'value="1"' in body
    assert 'value="12"' in body
    assert 'value="6"' in body
    assert 'value="custom"' in body
    # Direction controls
    assert 'value="IN"' in body
    assert 'value="OUT"' in body
    assert 'value="ADJUST"' in body
    # Autofocus
    assert "autofocus" in body
    # Vendored assets referenced
    assert "/static/js/htmx.min.js" in body
    assert "/static/js/alpine.min.js" in body


# ---------------------------------------------------------------------- #
# POST /scan — happy paths                                               #
# ---------------------------------------------------------------------- #


def test_post_scan_in_creates_stub_and_increments(client: TestClient) -> None:
    """POST /scan with direction=IN returns 200 HTML with the new on-hand."""
    response = client.post(
        "/scan",
        json={"gtin": "1234567890123", "direction": "IN", "qty_multiplier": 3, "location_id": 1},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    body = response.text
    # on-hand shows 3
    assert ">3<" in body
    # GTIN appears somewhere (either as title or detail)
    assert "1234567890123" in body


def test_post_scan_out_decrements_on_hand(client: TestClient) -> None:
    """IN then OUT at the same GTIN reduces on-hand."""
    gtin = "1111111111111"
    client.post(
        "/scan",
        json={"gtin": gtin, "direction": "IN", "qty_multiplier": 10, "location_id": 1},
    )
    response = client.post(
        "/scan",
        json={"gtin": gtin, "direction": "OUT", "qty_multiplier": 4, "location_id": 1},
    )
    assert response.status_code == 200
    # 10 - 4 = 6 on hand
    assert ">6<" in response.text


# ---------------------------------------------------------------------- #
# POST /scan — error paths (M2 exit criteria: "clear error" on over-out) #
# ---------------------------------------------------------------------- #


def test_post_scan_over_scan_out_returns_409_with_clear_error(client: TestClient) -> None:
    """Over-scan-out returns 409 Conflict with a human-readable message."""
    gtin = "2222222222222"
    client.post(
        "/scan",
        json={"gtin": gtin, "direction": "IN", "qty_multiplier": 2, "location_id": 1},
    )
    response = client.post(
        "/scan",
        json={"gtin": gtin, "direction": "OUT", "qty_multiplier": 99, "location_id": 1},
    )
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "Cannot remove" in detail
    assert "99" in detail
    assert "only 2 on hand" in detail


def test_post_scan_unknown_location_returns_404(client: TestClient) -> None:
    """Non-existent location returns 404 with a clear error."""
    response = client.post(
        "/scan",
        json={"gtin": "3333333333333", "direction": "IN", "qty_multiplier": 1, "location_id": 999},
    )
    assert response.status_code == 404
    assert "Location 999" in response.json()["detail"]


# ---------------------------------------------------------------------- #
# POST /scan — validation (422 instead of 500)                            #
# ---------------------------------------------------------------------- #


def test_post_scan_invalid_direction_returns_422(client: TestClient) -> None:
    """Invalid direction values are rejected at the edge, not at the DB."""
    response = client.post(
        "/scan",
        json={"gtin": "4444444444444", "direction": "BOGUS", "qty_multiplier": 1, "location_id": 1},
    )
    # Must be 422, never 500 (regression for issue #9)
    assert response.status_code == 422


def test_post_scan_lowercase_direction_returns_422(client: TestClient) -> None:
    """Direction enum is case-sensitive; \"in\" is not \"IN\"."""
    response = client.post(
        "/scan",
        json={"gtin": "4444444444444", "direction": "in", "qty_multiplier": 1, "location_id": 1},
    )
    assert response.status_code == 422


def test_post_scan_empty_gtin_returns_422(client: TestClient) -> None:
    """Empty GTIN is rejected by the min_length constraint."""
    response = client.post(
        "/scan",
        json={"gtin": "", "direction": "IN", "qty_multiplier": 1, "location_id": 1},
    )
    assert response.status_code == 422


def test_post_scan_short_gtin_returns_422(client: TestClient) -> None:
    """GTIN shorter than 6 characters is rejected."""
    response = client.post(
        "/scan",
        json={"gtin": "12345", "direction": "IN", "qty_multiplier": 1, "location_id": 1},
    )
    assert response.status_code == 422


def test_post_scan_zero_qty_multiplier_returns_422(client: TestClient) -> None:
    """qty_multiplier=0 is a no-op and rejected as nonsensical."""
    response = client.post(
        "/scan",
        json={"gtin": "5555555555555", "direction": "IN", "qty_multiplier": 0, "location_id": 1},
    )
    assert response.status_code == 422


def test_post_scan_negative_qty_multiplier_returns_422(client: TestClient) -> None:
    """Negative qty_multiplier with direction=IN is semantically incoherent."""
    response = client.post(
        "/scan",
        json={"gtin": "5555555555555", "direction": "IN", "qty_multiplier": -3, "location_id": 1},
    )
    assert response.status_code == 422


def test_post_scan_missing_body_returns_422(client: TestClient) -> None:
    """Empty body fails Pydantic validation (missing gtin)."""
    response = client.post("/scan", json={})
    assert response.status_code == 422
