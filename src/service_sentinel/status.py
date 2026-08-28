"""Read and evaluate the latest stored service status."""

from decimal import Decimal
from typing import Protocol

import boto3

HEALTHY = "HEALTHY"
UNHEALTHY = "UNHEALTHY"
UNKNOWN = "UNKNOWN"
KNOWN_STATUSES = {HEALTHY, UNHEALTHY}

StatusItem = dict[str, str | int | Decimal]
StatusResponse = dict[str, str | int | None]


class StatusReader(Protocol):
    """Interface for retrieving one service's latest status record."""

    def get(self, service_name: str) -> StatusItem | None:
        """Return the stored status record, or None when it is missing."""


class DynamoDBStatusReader:
    """Retrieve current service status from DynamoDB."""

    def __init__(self, table_name: str) -> None:
        self._table = boto3.resource("dynamodb").Table(table_name)

    def get(self, service_name: str) -> StatusItem | None:
        response = self._table.get_item(
            Key={"service_name": service_name},
            ConsistentRead=True,
        )
        return response.get("Item")


def build_status_response(
    item: StatusItem | None,
    *,
    service_name: str,
    now: int,
    stale_after_seconds: int,
) -> StatusResponse:
    """Convert a stored record into the conservative public status response."""
    if item is None:
        return _unknown_response(service_name, checked_at=None)

    try:
        checked_at = int(item["checked_at"])
    except (KeyError, TypeError, ValueError):
        return _unknown_response(service_name, checked_at=None)

    stored_status = item.get("status")
    is_stale = now - checked_at > stale_after_seconds

    if stored_status not in KNOWN_STATUSES or is_stale:
        return _unknown_response(service_name, checked_at=checked_at)

    return {
        "status": str(stored_status),
        "service": service_name,
        "checked_at": checked_at,
    }


def _unknown_response(service_name: str, checked_at: int | None) -> StatusResponse:
    return {
        "status": UNKNOWN,
        "service": service_name,
        "checked_at": checked_at,
    }
