"""Smoke-test a Service Sentinel monitor Lambda alias."""

import argparse
import json
import os
from typing import Any

import boto3

SERVICE_NAME = "service-sentinel-api"


def invoke_monitor(
    *,
    function_name: str,
    alias: str,
    expected_lambda_version: str | None,
    region: str,
    profile: str | None,
) -> dict[str, Any]:
    """Invoke the monitor alias and validate the Lambda invocation metadata."""
    session = boto3.Session(profile_name=profile, region_name=region)
    lambda_client = session.client("lambda")
    response = lambda_client.invoke(
        FunctionName=function_name,
        Qualifier=alias,
        InvocationType="RequestResponse",
        Payload=b"{}",
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

    return payload


def validate_observation(observation: dict[str, Any]) -> None:
    """Validate the monitor's complete observation contract."""
    expected_fields = {"checked_at", "service_name", "status"}
    if set(observation) != expected_fields:
        raise RuntimeError(
            f"Unexpected monitor fields: {sorted(observation)}"
        )

    if observation["service_name"] != SERVICE_NAME:
        raise RuntimeError(f"Unexpected monitor service: {observation}")

    if observation["status"] != "HEALTHY":
        raise RuntimeError(f"Monitor did not observe HEALTHY: {observation}")

    checked_at = observation["checked_at"]
    if not isinstance(checked_at, int) or checked_at <= 0:
        raise RuntimeError(f"Monitor returned an invalid checked_at: {observation}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alias", choices=("candidate", "production"), required=True)
    parser.add_argument("--expected-lambda-version")
    parser.add_argument("--function-name", default="service-sentinel-monitor")
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "us-west-1"))
    parser.add_argument("--profile")
    args = parser.parse_args()

    observation = invoke_monitor(
        function_name=args.function_name,
        alias=args.alias,
        expected_lambda_version=args.expected_lambda_version,
        region=args.region,
        profile=args.profile,
    )
    validate_observation(observation)
    print(json.dumps(observation, indent=2, sort_keys=True))
    print(f"{args.alias} monitor smoke test passed.")


if __name__ == "__main__":
    main()
