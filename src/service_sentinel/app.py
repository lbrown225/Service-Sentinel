"""FastAPI application and AWS Lambda adapter."""

from fastapi import FastAPI
from mangum import Mangum

from service_sentinel import __version__

SERVICE_NAME = "service-sentinel-api"

app = FastAPI(title="Service Sentinel API", version=__version__)


@app.get("/health")
def health() -> dict[str, str]:
    """Return API liveness and identity information."""
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": __version__,
    }


handler = Mangum(app)
