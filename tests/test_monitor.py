"""Tests for the scheduled service health monitor."""

import json
from urllib.request import Request

import pytest

import service_sentinel.monitor as monitor_module
from service_sentinel.status import HEALTHY, UNHEALTHY

NOW = 2_000_000_000


class FakeHTTPResponse:
    """Provide the parts of an urllib response used by the monitor."""

    def __init__(self, status: int, body: dict[str, str]) -> None:
        self.status = status
        self._body = json.dumps(body).encode("utf-8")

    def __enter__(self) -> FakeHTTPResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_check_health_returns_healthy_for_exact_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_body = {
        "status": "healthy",
        "service": "service-sentinel-api",
        "version": "0.1.0",
    }

    def fake_urlopen(request: Request, timeout: int) -> FakeHTTPResponse:
        assert request.full_url == "https://example.com/health"
        assert request.get_method() == "GET"
        assert request.get_header("Accept") == "application/json"
        assert timeout == 5
        return FakeHTTPResponse(200, expected_body)

    monkeypatch.setattr(monitor_module, "urlopen", fake_urlopen)

    assert monitor_module.check_health("https://example.com/health", 5) == HEALTHY


def test_check_health_returns_unhealthy_for_non_200_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        monitor_module,
        "urlopen",
        lambda request, timeout: FakeHTTPResponse(503, {}),
    )

    assert monitor_module.check_health("https://example.com/health", 5) == UNHEALTHY


def test_check_health_returns_unhealthy_for_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_timeout(request: Request, timeout: int) -> FakeHTTPResponse:
        raise TimeoutError

    monkeypatch.setattr(monitor_module, "urlopen", raise_timeout)

    assert monitor_module.check_health("https://example.com/health", 5) == UNHEALTHY


def test_check_health_returns_unhealthy_for_unexpected_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    unexpected_body = {
        "status": "healthy",
        "service": "wrong-service",
        "version": "0.1.0",
    }
    monkeypatch.setattr(
        monitor_module,
        "urlopen",
        lambda request, timeout: FakeHTTPResponse(200, unexpected_body),
    )

    assert monitor_module.check_health("https://example.com/health", 5) == UNHEALTHY


def test_write_status_puts_exact_item_in_dynamodb(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    written_items: list[dict[str, str | int]] = []

    class FakeTable:
        def put_item(self, *, Item: dict[str, str | int]) -> None:
            written_items.append(Item)

    class FakeDynamoDB:
        def Table(self, table_name: str) -> FakeTable:
            assert table_name == "service-sentinel-status"
            return FakeTable()

    def fake_resource(service_name: str) -> FakeDynamoDB:
        assert service_name == "dynamodb"
        return FakeDynamoDB()

    monkeypatch.setattr(monitor_module.boto3, "resource", fake_resource)

    monitor_module.write_status("service-sentinel-status", HEALTHY, NOW)

    assert written_items == [
        {
            "service_name": "service-sentinel-api",
            "status": "HEALTHY",
            "checked_at": NOW,
        }
    ]


def test_handler_checks_and_writes_status(monkeypatch: pytest.MonkeyPatch) -> None:
    write_arguments: list[tuple[str, str, int]] = []

    def fake_check_health(health_endpoint: str, timeout_seconds: int) -> str:
        assert health_endpoint == "https://example.com/health"
        assert timeout_seconds == 7
        return HEALTHY

    def fake_write_status(table_name: str, status: str, checked_at: int) -> None:
        write_arguments.append((table_name, status, checked_at))

    monkeypatch.setenv("HEALTH_ENDPOINT", "https://example.com/health")
    monkeypatch.setenv("STATUS_TABLE_NAME", "service-sentinel-status")
    monkeypatch.setenv("HEALTH_CHECK_TIMEOUT_SECONDS", "7")
    monkeypatch.setattr(monitor_module, "time", lambda: NOW)
    monkeypatch.setattr(monitor_module, "check_health", fake_check_health)
    monkeypatch.setattr(monitor_module, "write_status", fake_write_status)

    result = monitor_module.handler({}, object())

    assert write_arguments == [("service-sentinel-status", HEALTHY, NOW)]
    assert result == {
        "service_name": "service-sentinel-api",
        "status": "HEALTHY",
        "checked_at": NOW,
    }
