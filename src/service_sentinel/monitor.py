"""Check the public health endpoint and store its current status."""

import json
import logging
import os
from time import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import boto3

from service_sentinel import __version__
from service_sentinel.status import HEALTHY, UNHEALTHY

SERVICE_NAME = "service-sentinel-api"
DEFAULT_TIMEOUT_SECONDS = 5

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def check_health(health_endpoint: str, timeout_seconds: int) -> str:
    """Return HEALTHY only when the endpoint returns the exact expected response."""
    request = Request(
        health_endpoint,
        headers={"Accept": "application/json"},
        method="GET",
    )

    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            if response.status != 200:
                return UNHEALTHY

            response_body = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
        return UNHEALTHY

    expected_body = {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": __version__,
    }
    return HEALTHY if response_body == expected_body else UNHEALTHY


def write_status(table_name: str, status: str, checked_at: int) -> None:
    """Replace the service's current DynamoDB status record."""
    table = boto3.resource("dynamodb").Table(table_name)
    table.put_item(
        Item={
            "service_name": SERVICE_NAME,
            "status": status,
            "checked_at": checked_at,
        }
    )


def handler(_event: object, _context: object) -> dict[str, str | int]:
    """Run one scheduled health check and persist its observation."""
    health_endpoint = os.environ["HEALTH_ENDPOINT"]
    table_name = os.environ["STATUS_TABLE_NAME"]
    timeout_seconds = int(
        os.environ.get("HEALTH_CHECK_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
    )
    checked_at = int(time())

    status = check_health(health_endpoint, timeout_seconds)
    write_status(table_name, status, checked_at)

    observation = {
        "service_name": SERVICE_NAME,
        "status": status,
        "checked_at": checked_at,
    }
    logger.info(json.dumps(observation))
    return observation
