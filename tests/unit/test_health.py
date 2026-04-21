"""Tests for health check endpoints."""

from fastapi.testclient import TestClient

from inv import __version__


def test_health_endpoint(client: TestClient) -> None:
    """Test /health endpoint returns 200."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == __version__


def test_version_endpoint(client: TestClient) -> None:
    """Test /version endpoint."""
    response = client.get("/version")
    assert response.status_code == 200
    data = response.json()
    assert data["version"] == __version__
