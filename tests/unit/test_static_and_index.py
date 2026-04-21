"""Tests for static-asset mounting and the M1 index page."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_index_renders_base_template(client: TestClient) -> None:
    """`/` returns 200 HTML (not a redirect to a missing /scan route)."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    # Sanity check: the vendored asset URLs are referenced in the rendered page.
    body = response.text
    assert "/static/css/pico.min.css" in body
    assert "/static/js/htmx.min.js" in body
    assert "/static/js/alpine.min.js" in body


def test_static_htmx_served(client: TestClient) -> None:
    """Real HTMX is served (not the placeholder stub)."""
    response = client.get("/static/js/htmx.min.js")
    assert response.status_code == 200
    # Real HTMX is >40 KB; the old placeholder was ~100 bytes.
    assert len(response.content) > 20_000
    # Sanity check the minified file starts with the known HTMX preamble.
    assert response.text.lstrip().startswith("var htmx")


def test_static_alpine_served(client: TestClient) -> None:
    """Real Alpine.js is served."""
    response = client.get("/static/js/alpine.min.js")
    assert response.status_code == 200
    assert len(response.content) > 20_000


def test_static_pico_served(client: TestClient) -> None:
    """Real Pico.css is served."""
    response = client.get("/static/css/pico.min.css")
    assert response.status_code == 200
    assert len(response.content) > 20_000
    assert "Pico" in response.text[:500]


def test_static_scan_focus_served(client: TestClient) -> None:
    """First-party scan-focus helper is served."""
    response = client.get("/static/js/scan_focus.js")
    assert response.status_code == 200
    assert b"htmx:afterSwap" in response.content
