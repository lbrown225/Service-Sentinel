"""Tests for the Service Sentinel health endpoint."""

from fastapi.testclient import TestClient

from service_sentinel.app import app

client = TestClient(app)


def test_health_returns_expected_response() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "service-sentinel-api",
        "version": "0.1.0",
    }
