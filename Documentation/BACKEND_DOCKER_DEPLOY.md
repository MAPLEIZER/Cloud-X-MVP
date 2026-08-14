# Cloud-X Local Docker Deployment

> **Status:** development / validation only. Cloud-X does not currently publish supported backend or frontend images to GHCR.

This document describes the current local/container validation path. Release-image publishing will return only after Phase 0 establishes versioned release artifacts, SBOM/provenance, signing, compatibility metadata and a supported upgrade/rollback process.

## Current CI rule

The normal `.github/workflows/docker-build.yml` workflow is the container gate. It builds both frontend and backend images, verifies the backend runs unprivileged, smoke-tests Nmap as that runtime user, applies the database migrations to a clean PostgreSQL instance, and runs the backend regression suite.

There is intentionally **no** always-on image publishing workflow during this phase. A successful build proves that the images can be constructed and validated; it does not publish mutable `latest` images as a side effect of merging code.

## Backend stack

The backend container is defined by `cloudx-flask-backend/Dockerfile`. The validation stack in `cloudx-flask-backend/docker-compose.yml` contains:

- PostgreSQL 17 with a persistent named volume;
- the Cloud-X backend image running as UID/GID 10001;
- a separate `/data` volume for node identity/runtime state;
- `cap_drop: ALL`, with only `NET_RAW` restored for scanning;
- `no-new-privileges`;
- PostgreSQL and backend health checks.

From the repository root:

```bash
cd cloudx-flask-backend
cp .env.example .env
# Replace Clerk and PostgreSQL placeholders before starting.
docker compose build
docker compose up -d
docker compose ps
curl -fsS http://127.0.0.1:5001/api/health
```

The backend requires `DATABASE_URL`. Container startup runs `alembic upgrade head` before Gunicorn starts, so a new PostgreSQL database receives the versioned schema automatically. Production startup no longer uses `db.create_all()` and does not use a SQLite `scans.db` file.

To inspect migrations manually:

```bash
docker compose run --rm backend alembic current
docker compose run --rm backend alembic history
docker compose run --rm backend alembic upgrade head
```

### Standalone installer

`install_backend.sh` remains an experimental bootstrap utility. It now generates or accepts PostgreSQL credentials, writes them to a mode-`0600` `.env`, starts PostgreSQL with a named volume, and starts the backend only after the database is healthy. It no longer creates or bind-mounts `scans.db`.

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

During Phase 0, build validation is useful; automatic image publication is not.

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
