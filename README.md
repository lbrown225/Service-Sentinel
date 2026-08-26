# Service Sentinel

Service Sentinel is a production-style AWS service health platform being built
for a DevOps/reliability portfolio interview.

This initial scaffold intentionally contains only the local Python core:

- `GET /health` reports whether the API process is serving requests.
- `GET /status` reports the latest monitored service state.
- Missing or stale monitoring data is always reported as `UNKNOWN`.
- The monitor classifies HTTP 2xx responses as `HEALTHY` and all other
  responses or request errors as `UNHEALTHY`.

The in-memory repository is only a local development seam. A later increment
will provide the DynamoDB implementation used by the two Lambda functions.

## Requirements

- Python 3.14+

There are no third-party runtime or test dependencies in this increment.

## Run locally

Start the API:

```powershell
python -m service_sentinel.api
```

Then query it in another terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/health
Invoke-RestMethod http://127.0.0.1:8080/status
```

Run the tests:

```powershell
python -m unittest discover -s tests -v
```

