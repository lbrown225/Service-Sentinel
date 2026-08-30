"""Smoke-test the API handler through the local Lambda runtime endpoint."""

import argparse
import json
import time
from datetime import UTC, datetime
from urllib.error import URLError
from urllib.request import Request, urlopen

DEFAULT_INVOCATION_URI = "http://localhost:9000/2015-03-31/functions/function/invocations"
EXPECTED_HEALTH = {
    "status": "healthy",
    "service": "service-sentinel-api",
    "version": "0.1.0",
}


def build_health_event() -> dict[str, object]:
    """Build the API Gateway v2 event that Mangum expects."""
    now = datetime.now(UTC)
    timestamp_ms = int(now.timestamp() * 1000)

    return {
        "version": "2.0",
        "routeKey": "GET /health",
        "rawPath": "/health",
        "rawQueryString": "",
        "headers": {"host": "localhost"},
        "requestContext": {
            "accountId": "local",
            "apiId": "local",
            "domainName": "localhost",
            "domainPrefix": "localhost",
            "http": {
                "method": "GET",
                "path": "/health",
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "smoke_api_local_container.py",
            },
            "requestId": f"local-{timestamp_ms}",
            "routeKey": "GET /health",
            "stage": "$default",
            "time": now.strftime("%d/%b/%Y:%H:%M:%S +0000"),
            "timeEpoch": timestamp_ms,
        },
        "isBase64Encoded": False,
    }


def invoke_health(invocation_uri: str, timeout_seconds: float) -> dict[str, object]:
    """Invoke the local Lambda runtime and return its decoded response."""
    payload = json.dumps(build_health_event()).encode("utf-8")
    request = Request(
        invocation_uri,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urlopen(request, timeout=timeout_seconds) as response:
        return json.loads(response.read().decode("utf-8"))


def smoke_test(
    invocation_uri: str,
    *,
    attempts: int,
    delay_seconds: float,
    timeout_seconds: float,
) -> None:
    """Retry startup failures, then validate the complete health response."""
    lambda_response: dict[str, object] | None = None
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            lambda_response = invoke_health(invocation_uri, timeout_seconds)
            break
        except (TimeoutError, URLError) as error:
            last_error = error
            if attempt < attempts:
                time.sleep(delay_seconds)

    if lambda_response is None:
        raise RuntimeError(
            f"Local Lambda invocation failed after {attempts} attempts: {last_error}"
        )

    if lambda_response.get("statusCode") != 200:
        raise RuntimeError(f"Lambda returned an unexpected response: {lambda_response}")

    response_body = lambda_response.get("body")
    if not isinstance(response_body, str):
        raise RuntimeError(f"Lambda response body was not JSON text: {lambda_response}")

    health_response = json.loads(response_body)
    if health_response != EXPECTED_HEALTH:
        raise RuntimeError(f"Unexpected health response: {health_response}")

    print(json.dumps(health_response, indent=2))
    print("Local container smoke test passed.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--invocation-uri", default=DEFAULT_INVOCATION_URI)
    parser.add_argument("--attempts", type=int, default=10)
    parser.add_argument("--delay-seconds", type=float, default=1.0)
    parser.add_argument("--timeout-seconds", type=float, default=5.0)
    args = parser.parse_args()

    smoke_test(
        args.invocation_uri,
        attempts=args.attempts,
        delay_seconds=args.delay_seconds,
        timeout_seconds=args.timeout_seconds,
    )


if __name__ == "__main__":
    main()
