import json
import unittest
from datetime import UTC, datetime, timedelta

from service_sentinel.api import SERVICE_NAME, lambda_handler, route
from service_sentinel.repository import InMemoryStatusRepository
from service_sentinel.status import HealthState, ServiceStatus


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repository = InMemoryStatusRepository()
        self.now = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)

    def test_health_reports_api_liveness(self) -> None:
        status_code, body = route("GET", "/health")

        self.assertEqual(200, status_code)
        self.assertEqual("HEALTHY", body["status"])

    def test_status_is_unknown_when_data_is_missing(self) -> None:
        status_code, body = route(
            "GET", "/status", status_repository=self.repository, now=self.now
        )

        self.assertEqual(200, status_code)
        self.assertEqual("UNKNOWN", body["status"])
        self.assertEqual("NO_DATA", body["reason"])

    def test_status_is_unknown_when_data_is_stale(self) -> None:
        self.repository.put(
            ServiceStatus(
                SERVICE_NAME,
                HealthState.HEALTHY,
                self.now - timedelta(minutes=3),
            )
        )

        _, body = route(
            "GET", "/status", status_repository=self.repository, now=self.now
        )

        self.assertEqual("UNKNOWN", body["status"])
        self.assertEqual("STALE_DATA", body["reason"])

    def test_status_returns_fresh_result(self) -> None:
        self.repository.put(
            ServiceStatus(SERVICE_NAME, HealthState.UNHEALTHY, self.now, "HTTP_503")
        )

        _, body = route(
            "GET", "/status", status_repository=self.repository, now=self.now
        )

        self.assertEqual("UNHEALTHY", body["status"])
        self.assertEqual("HTTP_503", body["reason"])

    def test_lambda_handler_returns_api_gateway_response(self) -> None:
        response = lambda_handler(
            {"rawPath": "/health", "requestContext": {"http": {"method": "GET"}}},
            None,
        )

        self.assertEqual(200, response["statusCode"])
        self.assertEqual("HEALTHY", json.loads(response["body"])["status"])


if __name__ == "__main__":
    unittest.main()

