"""Tests for the Service Sentinel status endpoint."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

import service_sentinel.app as app_module
from service_sentinel.status import StatusItem

NOW = 2_000_000_000


class FakeStatusReader:
    """Return a predefined record without contacting DynamoDB."""

    def __init__(self, item: StatusItem | None) -> None:
        self._item = item

    def get(self, service_name: str) -> StatusItem | None:
        assert service_name == "service-sentinel-api"
        return self._item


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(app_module, "time", lambda: NOW)
    return TestClient(app_module.app)


def request_status(client: TestClient, item: StatusItem | None) -> dict[str, object]:
    app_module.app.dependency_overrides[app_module.get_status_reader] = lambda: FakeStatusReader(
        item
    )

    try:
        response = client.get("/status")
    finally:
        app_module.app.dependency_overrides.clear()

    assert response.status_code == 200
    return response.json()


def test_status_returns_fresh_healthy_record(client: TestClient) -> None:
    response = request_status(
        client,
        {
            "service_name": "service-sentinel-api",
            "status": "HEALTHY",
            "checked_at": Decimal(NOW - 60),
        },
    )

    assert response == {
        "status": "HEALTHY",
        "service": "service-sentinel-api",
        "checked_at": NOW - 60,
    }


def test_status_returns_fresh_unhealthy_record(client: TestClient) -> None:
    response = request_status(
        client,
        {
            "service_name": "service-sentinel-api",
            "status": "UNHEALTHY",
            "checked_at": Decimal(NOW - 60),
        },
    )

    assert response == {
        "status": "UNHEALTHY",
        "service": "service-sentinel-api",
        "checked_at": NOW - 60,
    }


def test_status_returns_unknown_when_record_is_missing(client: TestClient) -> None:
    response = request_status(client, None)

    assert response == {
        "status": "UNKNOWN",
        "service": "service-sentinel-api",
        "checked_at": None,
    }


def test_status_returns_unknown_when_record_is_stale(client: TestClient) -> None:
    response = request_status(
        client,
        {
            "service_name": "service-sentinel-api",
            "status": "HEALTHY",
            "checked_at": Decimal(NOW - 301),
        },
    )

    assert response == {
        "status": "UNKNOWN",
        "service": "service-sentinel-api",
        "checked_at": NOW - 301,
    }
