# Service Sentinel

Milestone 1 is a minimal FastAPI service with a health endpoint and a Mangum
adapter for a future AWS Lambda deployment. It contains no AWS infrastructure,
monitoring logic, container configuration, or frontend.

## Requirements

- Python 3.14+

## Run locally

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the application and development dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Run linting and tests:

```powershell
ruff check .
pytest
```

The API application is `service_sentinel.app:app`. The Lambda entry point is
`service_sentinel.app.handler`.
