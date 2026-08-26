import unittest
from datetime import UTC, datetime

from service_sentinel.monitor import check_url, run_monitor
from service_sentinel.repository import InMemoryStatusRepository
from service_sentinel.status import HealthState, ServiceStatus


class FakeResponse:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class MonitorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)

    def test_2xx_response_is_healthy(self) -> None:
        result = check_url(
            "https://example.test/health",
            opener=lambda *_args, **_kwargs: FakeResponse(204),
            clock=lambda: self.now,
        )

        self.assertEqual(HealthState.HEALTHY, result.status)
        self.assertIsNone(result.reason)
        self.assertEqual(self.now, result.checked_at)

    def test_non_2xx_response_is_unhealthy(self) -> None:
        result = check_url(
            "https://example.test/health",
            opener=lambda *_args, **_kwargs: FakeResponse(503),
            clock=lambda: self.now,
        )

        self.assertEqual(HealthState.UNHEALTHY, result.status)
        self.assertEqual("HTTP_503", result.reason)

    def test_request_error_is_unhealthy(self) -> None:
        def failing_opener(*_args: object, **_kwargs: object) -> FakeResponse:
            raise TimeoutError("timed out")

        result = check_url(
            "https://example.test/health",
            opener=failing_opener,
            clock=lambda: self.now,
        )

        self.assertEqual(HealthState.UNHEALTHY, result.status)
        self.assertEqual("TimeoutError", result.reason)

    def test_run_monitor_persists_result(self) -> None:
        repository = InMemoryStatusRepository()
        expected = ServiceStatus("service-sentinel", HealthState.HEALTHY, self.now)

        result = run_monitor(
            "https://example.test/health",
            status_repository=repository,
            checker=lambda _url: expected,
        )

        self.assertEqual(expected, result)
        self.assertEqual(expected, repository.get("service-sentinel"))


if __name__ == "__main__":
    unittest.main()
