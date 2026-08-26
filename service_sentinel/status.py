"""Health status domain model and freshness rules."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum


class HealthState(StrEnum):
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    service: str
    status: HealthState
    checked_at: datetime | None
    reason: str | None = None
    latency_ms: int | None = None

    def to_dict(self) -> dict[str, str | int | None]:
        payload = asdict(self)
        payload["status"] = self.status.value
        payload["checked_at"] = (
            self.checked_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
            if self.checked_at
            else None
        )
        return payload


def public_status(
    latest: ServiceStatus | None,
    *,
    service: str,
    now: datetime,
    stale_after: timedelta,
) -> ServiceStatus:
    """Return a fail-safe public status derived from the latest observation."""
    if latest is None:
        return ServiceStatus(service, HealthState.UNKNOWN, None, "NO_DATA")

    checked_at = latest.checked_at
    if checked_at is None or now - checked_at > stale_after:
        return ServiceStatus(
            service,
            HealthState.UNKNOWN,
            checked_at,
            "STALE_DATA",
            latest.latency_ms,
        )

    return latest

