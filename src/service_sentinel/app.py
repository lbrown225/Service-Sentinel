"""FastAPI application and AWS Lambda adapter."""

import os
from functools import lru_cache
from time import time
from typing import Annotated

from fastapi import Depends, FastAPI
from mangum import Mangum

from service_sentinel import __version__
from service_sentinel.status import (
    DynamoDBStatusReader,
    StatusReader,
    StatusResponse,
    build_status_response,
)

SERVICE_NAME = "service-sentinel-api"
DEFAULT_STALE_AFTER_SECONDS = 300

app = FastAPI(title="Service Sentinel API", version=__version__)


@lru_cache
def get_status_reader() -> StatusReader:
    """Create and reuse the DynamoDB status reader."""
    table_name = os.environ["STATUS_TABLE_NAME"]
    return DynamoDBStatusReader(table_name)


@app.get("/health")
def health() -> dict[str, str]:
    """Return API liveness and identity information."""
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": __version__,
    }


@app.get("/status")
def status(reader: Annotated[StatusReader, Depends(get_status_reader)]) -> StatusResponse:
    """Return the latest status, treating missing or stale data as unknown."""
    stale_after_seconds = int(
        os.environ.get("STATUS_STALE_AFTER_SECONDS", DEFAULT_STALE_AFTER_SECONDS)
    )
    item = reader.get(SERVICE_NAME)

    return build_status_response(
        item,
        service_name=SERVICE_NAME,
        now=int(time()),
        stale_after_seconds=stale_after_seconds,
    )


handler = Mangum(app)
