"""Smoke-test Service Sentinel API candidate or production endpoints."""

import argparse
import json
import os
from datetime import UTC, datetime
from typing import Any
from urllib.request import Request, urlopen

import boto3

SERVICE_NAME = "service-sentinel-api"
SERVICE_VERSION = "0.1.0"
STATUS_CHOICES = ("UNKNOWN", "HEALTHY", "UNHEALTHY")


def build_api_gateway_event(route: str) -> dict[str, object]:
    """Build an API Gateway v2 event for direct candidate invocation."""
    now = datetime.now(UTC)
    timestamp_ms = int(now.timestamp() * 1000)
    request_path = f"/{route}"
    route_key = f"GET {request_path}"

    return {
        "version": "2.0",
        "routeKey": route_key,
        "rawPath": request_path,
        "rawQueryString": "",
        "headers": {"host": "candidate.internal"},
        "requestContext": {
            "accountId": "smoke-test",
            "apiId": "smoke-test",
            "domainName": "candidate.internal",
            "domainPrefix": "candidate",
            "http": {
                "method": "GET",
                "path": request_path,
                "protocol": "HTTP/1.1",
                "sourceIp": "127.0.0.1",
                "userAgent": "smoke_api.py",
            },
            "requestId": f"candidate-{route}-{timestamp_ms}",
            "routeKey": route_key,
            "stage": "$default",
            "time": now.strftime("%d/%b/%Y:%H:%M:%S +0000"),
            "timeEpoch": timestamp_ms,
        },
        "isBase64Encoded": False,
    }


def invoke_candidate(
    *,
    function_name: str,
    alias: str,
    route: str,
    expected_lambda_version: str | None,
    region: str,
    profile: str | None,
) -> dict[str, object]:
    """Invoke an API Lambda alias and decode its HTTP-style response."""
    session = boto3.Session(profile_name=profile, region_name=region)
    lambda_client = session.client("lambda")
    response = lambda_client.invoke(
        FunctionName=function_name,
        Qualifier=alias,
        InvocationType="RequestResponse",
        Payload=json.dumps(build_api_gateway_event(route)).encode("utf-8"),
    )

    if response.get("StatusCode") != 200:
        raise RuntimeError(f"AWS Lambda invocation failed: {response}")

    payload = json.loads(response["Payload"].read().decode("utf-8"))
    if response.get("FunctionError"):
        raise RuntimeError(f"Lambda reported a function error: {payload}")

    executed_version = str(response.get("ExecutedVersion", ""))
    if expected_lambda_version and executed_version != expected_lambda_version:
        raise RuntimeError(
            f"Expected Lambda version {expected_lambda_version}, "
            f"but executed {executed_version}."
        )

    if payload.get("statusCode") != 200:
        raise RuntimeError(f"API handler returned an unexpected response: {payload}")

    body = payload.get("body")
    if not isinstance(body, str):
        raise RuntimeError(f"API handler body was not JSON text: {payload}")

    return json.loads(body)


def request_production(*, api_base_url: str, route: str) -> dict[str, object]:
    """Request a route through the public production API Gateway endpoint."""
    endpoint = f"{api_base_url.rstrip('/')}/{route}"
    request = Request(endpoint, method="GET")

    with urlopen(request, timeout=10) as response:
        if response.status != 200:
            raise RuntimeError(f"Production API returned HTTP {response.status}.")
        return json.loads(response.read().decode("utf-8"))


def validate_api_response(
    response: dict[str, Any], *, route: str, expected_status: str
) -> None:
    """Validate the complete health or status response contract."""
    expected_fields = (
        {"service", "status", "version"}
        if route == "health"
        else {"checked_at", "service", "status"}
    )
    if set(response) != expected_fields:
        raise RuntimeError(f"Unexpected {route} response fields: {sorted(response)}")

    if response["service"] != SERVICE_NAME:
        raise RuntimeError(f"Unexpected service name: {response}")

    if route == "health":
        expected = {
            "status": "healthy",
            "service": SERVICE_NAME,
            "version": SERVICE_VERSION,
        }
        if response != expected:
            raise RuntimeError(f"Unexpected health response: {response}")
        return

    if response["status"] != expected_status:
        raise RuntimeError(f"Unexpected status response: {response}")

    checked_at = response["checked_at"]
    if expected_status != "UNKNOWN" and (
        not isinstance(checked_at, int) or checked_at <= 0
    ):
        raise RuntimeError(f"Known status requires a positive checked_at: {response}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("candidate", "production"), required=True)
    parser.add_argument("--route", choices=("health", "status"), required=True)
    parser.add_argument("--expected-status", choices=STATUS_CHOICES, default="HEALTHY")
    parser.add_argument("--expected-lambda-version")
    parser.add_argument("--function-name", default="service-sentinel-api")
    parser.add_argument("--alias", default="candidate")
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-west-1"))
    parser.add_argument("--profile")
    parser.add_argument(
        "--api-base-url", default=os.getenv("SERVICE_SENTINEL_API_BASE_URL")
    )
    args = parser.parse_args()

    if args.target == "candidate":
        response = invoke_candidate(
            function_name=args.function_name,
            alias=args.alias,
            route=args.route,
            expected_lambda_version=args.expected_lambda_version,
            region=args.region,
            profile=args.profile,
        )
    else:
        if not args.api_base_url:
            parser.error(
                "--api-base-url or SERVICE_SENTINEL_API_BASE_URL is required "
                "for production"
            )
        response = request_production(api_base_url=args.api_base_url, route=args.route)

    validate_api_response(
        response,
        route=args.route,
        expected_status=args.expected_status,
    )
    print(json.dumps(response, indent=2, sort_keys=True))
    print(f"{args.target} API /{args.route} smoke test passed.")


if __name__ == "__main__":
    main()
