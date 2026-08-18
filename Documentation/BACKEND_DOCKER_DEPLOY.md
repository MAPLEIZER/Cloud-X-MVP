# Cloud-X Local Docker Deployment

> **Status:** development / validation only. Cloud-X does not currently publish supported backend or frontend images to GHCR.

This document describes the current local/container validation path. Release-image publishing will return only after versioned release artifacts, SBOM/provenance, signing, compatibility metadata and a supported upgrade/rollback process exist.

## Current CI rule

The normal `.github/workflows/docker-build.yml` workflow is the container gate. It builds both frontend and backend images, verifies the backend runs unprivileged, smoke-tests Nmap as that runtime user, applies database migrations to a clean PostgreSQL instance, starts Redis, enqueues work from one short-lived process, executes it in a separate RQ worker container, verifies persisted scan completion/cancellation state, and runs the backend regression suite.

There is intentionally **no** always-on image publishing workflow during this phase. A successful build proves that the images can be constructed and validated; it does not publish mutable `latest` images as a side effect of merging code.

## Backend stack

The backend container is defined by `cloudx-flask-backend/Dockerfile`. The validation stack in `cloudx-flask-backend/docker-compose.yml` contains:

- PostgreSQL 17 with a persistent named volume;
- Redis with append-only persistence in a named volume and no host-exposed port;
- the Cloud-X API image running as UID/GID 10001 with multiple Gunicorn workers supported;
- a separate RQ worker pool that owns scanner subprocesses;
- a separate `/data` volume for node identity/runtime state;
- `cap_drop: ALL`, with only `NET_RAW` restored where scanner functionality requires it;
- `no-new-privileges`;
- PostgreSQL, Redis and backend health checks.

From the repository root:

```bash
cd cloudx-flask-backend
cp .env.example .env
# Replace Clerk/PostgreSQL placeholders before starting.
docker compose build
docker compose up -d
docker compose ps
curl -fsS http://127.0.0.1:5001/api/health
```

The backend requires both `DATABASE_URL` and a reachable `REDIS_URL`. Container startup checks Redis, runs `alembic upgrade head`, reconciles any active PostgreSQL scan rows with RQ state, then starts Gunicorn. Production startup no longer uses `db.create_all()`, does not use a SQLite `scans.db`, and does not execute scanner jobs in Flask threads.

To inspect migrations manually:

```bash
docker compose run --rm backend alembic current
docker compose run --rm backend alembic history
docker compose run --rm backend alembic upgrade head
```

## Scan workers

The `scan-worker` service runs RQ against the `scans` queue using the JSON serializer and the custom `scan_jobs.CloudXWorker` class.

Operational knobs:

```env
REDIS_URL=redis://redis:6379/0
MAX_CONCURRENT_SCANS=4
SCAN_WORKERS=2
GUNICORN_WORKERS=2
GUNICORN_THREADS=4
```

Scale API and scanner execution independently. Increasing `GUNICORN_WORKERS` does not create more scanner subprocess slots; increase `SCAN_WORKERS` for worker parallelism and keep `MAX_CONCURRENT_SCANS` aligned with the resource budget of the host/network.

PostgreSQL is the source of truth for API-visible scan status/progress/results. Redis/RQ carries queue and cancellation control state. Queued jobs are canceled through RQ. Running scans use cooperative Redis cancellation so the worker that owns Nmap/ZMap/Masscan terminates its own child process cleanly rather than relying on an API-process handle.

Redis persistence helps queued/control state survive a Redis container restart, while PostgreSQL allows the API to recover and reconcile active scans after an API restart. The API fails scan submission with `503` when queue coordination is unavailable instead of falling back to non-durable local execution.

For an external Redis service, use an authenticated/TLS endpoint (`rediss://`) and restrict network access. Do not expose the Compose Redis port publicly.

### Standalone installer

`install_backend.sh` remains an experimental bootstrap utility. It generates or accepts PostgreSQL credentials, writes them to a mode-`0600` `.env`, starts PostgreSQL and Redis with named volumes, starts the backend after both dependencies are healthy, and starts the RQ scan-worker pool. It no longer creates or bind-mounts `scans.db`.

It accepts a locally available image or an explicitly supplied image tarball. Treat the script as a validation tool, not a production installer/release mechanism.

A future supported appliance installer must consume an immutable, versioned and verifiable Cloud-X release rather than a mutable `latest` registry tag, and should source credentials from an appropriate secret manager.

## Frontend

The validation compose file at `deploy/frontend/docker-compose.yml` builds the frontend locally from `Dockerfile.frontend` instead of pulling an unpublished GHCR image.

From the repository root:

```bash
FRONTEND_API_BASE_URL=http://localhost:5001 \
  docker compose -f deploy/frontend/docker-compose.yml build

docker compose -f deploy/frontend/docker-compose.yml up -d
docker compose -f deploy/frontend/docker-compose.yml ps
```

`FRONTEND_API_BASE_URL` is a build-time value for the current Vite image, so rebuild the frontend image when that value changes.

## Reverse proxy

The optional reverse-proxy files remain under `deploy/reverse-proxy/`. They can route frontend and backend traffic during local/private validation, but they do not imply a supported production topology.

## Why registry publishing is disabled

The previous GHCR workflows created two problems:

1. they published mutable `latest` images before Cloud-X had a release policy, signing/provenance and supported deployment contract;
2. repository documentation and deployment examples depended on images that were not consistently being produced successfully.

During the current hardening/Phase 1 work, build validation is useful; automatic image publication is not.

## When image publishing returns

Reintroduce container publishing as **one release workflow**, not separate always-on frontend/backend CI workflows, after these gates exist:

- version/tag based release trigger;
- immutable version and digest references;
- declared Wazuh compatibility manifest;
- generated SBOM;
- provenance/attestation;
- vulnerability and license-policy checks;
- signed/verifiable release artifacts;
- documented upgrade and rollback procedure;
- release notes and support status.

At that point deployment manifests should pin released image versions/digests rather than `latest`.

## Offline validation

For a temporary lab/offline host you may export a locally built image:

```bash
docker save cloudx-backend:latest -o cloudx-backend.tar
docker save cloudx-frontend:dev -o cloudx-frontend.tar
```

Load it on the target host with:

```bash
docker load -i cloudx-backend.tar
docker load -i cloudx-frontend.tar
```

This is a development convenience, not a release distribution mechanism.
