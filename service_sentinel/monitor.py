"""Service check logic and EventBridge-compatible Lambda handler."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, Callable
from urllib.request import urlopen

from service_sentinel.api import SERVICE_NAME, repository
from service_sentinel.repository import StatusRepository
from service_sentinel.status import HealthState, ServiceStatus


def check_url(
    url: str,
    *,
    service: str = SERVICE_NAME,
    timeout_seconds: float = 5.0,
    opener: Callable[..., Any] = urlopen,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> ServiceStatus:
    started = perf_counter()
    try:
        with opener(url, timeout=timeout_seconds) as response:
            status_code = response.status
        state = (
            HealthState.HEALTHY
            if 200 <= status_code < 300
            else HealthState.UNHEALTHY
        )
        reason = None if state is HealthState.HEALTHY else f"HTTP_{status_code}"
    except Exception as error:  # Boundary: network clients raise several error types.
        state = HealthState.UNHEALTHY
        reason = type(error).__name__

    latency_ms = round((perf_counter() - started) * 1000)
    return ServiceStatus(service, state, clock(), reason, latency_ms)


def run_monitor(
    url: str,
    *,
    status_repository: StatusRepository = repository,
    checker: Callable[..., ServiceStatus] = check_url,
) -> ServiceStatus:
    result = checker(url)
    status_repository.put(result)
    print(json.dumps({"event": "service_check", **result.to_dict()}))
    return result


def lambda_handler(_event: dict[str, Any], _context: Any) -> dict[str, Any]:
    target_url = os.environ["TARGET_URL"]
    return run_monitor(target_url).to_dict()

