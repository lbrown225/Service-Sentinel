"""Status persistence interfaces used by local code and future AWS adapters."""

from __future__ import annotations

from typing import Protocol

from service_sentinel.status import ServiceStatus


class StatusRepository(Protocol):
    def get(self, service: str) -> ServiceStatus | None: ...

    def put(self, status: ServiceStatus) -> None: ...


class InMemoryStatusRepository:
    def __init__(self) -> None:
        self._statuses: dict[str, ServiceStatus] = {}

    def get(self, service: str) -> ServiceStatus | None:
        return self._statuses.get(service)

    def put(self, status: ServiceStatus) -> None:
        self._statuses[status.service] = status

