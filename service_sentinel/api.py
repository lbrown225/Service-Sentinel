"""Local HTTP server and API Gateway-compatible Lambda handler."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime, timedelta
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from service_sentinel.repository import InMemoryStatusRepository, StatusRepository
from service_sentinel.status import HealthState, ServiceStatus, public_status

SERVICE_NAME = os.getenv("SERVICE_NAME", "service-sentinel")
STALE_AFTER = timedelta(seconds=int(os.getenv("STALE_AFTER_SECONDS", "120")))
repository: StatusRepository = InMemoryStatusRepository()


def route(
    method: str,
    path: str,
    *,
    status_repository: StatusRepository = repository,
    now: datetime | None = None,
) -> tuple[int, dict[str, Any]]:
    if method != "GET":
        return HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"}

    if path == "/health":
        return HTTPStatus.OK, {
            "service": SERVICE_NAME,
            "status": HealthState.HEALTHY.value,
        }

    if path == "/status":
        current = public_status(
            status_repository.get(SERVICE_NAME),
            service=SERVICE_NAME,
            now=now or datetime.now(UTC),
            stale_after=STALE_AFTER,
        )
        return HTTPStatus.OK, current.to_dict()

    return HTTPStatus.NOT_FOUND, {"error": "not_found"}


def lambda_handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Handle API Gateway HTTP API payloads."""
    method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("rawPath") or event.get("path") or "/"
    status_code, payload = route(method, path)
    return {
        "statusCode": int(status_code),
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload, separators=(",", ":")),
    }


class LocalRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        status_code, payload = route("GET", self.path.split("?", 1)[0])
        body = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status_code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        print(json.dumps({"event": "http_request", "message": format % args}))


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8080"))
    server = ThreadingHTTPServer((host, port), LocalRequestHandler)
    print(json.dumps({"event": "server_started", "host": host, "port": port}))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

