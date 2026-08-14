# Cloud-X Local Docker Deployment

> **Status:** development / validation only. Cloud-X does not currently publish supported backend or frontend images to GHCR.

This document describes the current local/container validation path. Release-image publishing will return only after Phase 0 establishes versioned release artifacts, SBOM/provenance, signing, compatibility metadata and a supported upgrade/rollback process.

## Current CI rule

The normal `.github/workflows/docker-build.yml` workflow is the container gate. It builds both the frontend and backend and runs the backend security regression suite.

There is intentionally **no** `Build and Push Backend Image` or `Build and Push Frontend Image` workflow during this phase. A successful build proves that the images can be constructed; it does not publish mutable `latest` images as a side effect of merging code.

## Backend

The backend container is defined by `cloudx-flask-backend/Dockerfile` and currently uses Python 3.14 slim. The repository compose file builds the image locally and names it `cloudx-backend:latest`.

From the repository root:

```bash
cd cloudx-flask-backend
cp .env.example .env
# Fill in the required Clerk/authentication settings before starting.
docker compose build
docker compose up -d
docker compose ps
curl -fsS http://127.0.0.1:5001/api/health
```

The compose configuration drops all Linux capabilities and adds back only `NET_RAW` for the scanner functionality. It also applies `no-new-privileges` and stores runtime state in the `cloudx_data` volume.

### Standalone installer

`install_backend.sh` remains an experimental bootstrap utility. It accepts a locally available image or an explicitly supplied image tarball. Treat the script as a validation tool, not a production installer/release mechanism.

A future supported appliance installer must consume an immutable, versioned and verifiable Cloud-X release rather than a mutable `latest` registry tag.

## Frontend

The validation compose file at `deploy/frontend/docker-compose.yml` now builds the frontend locally from `Dockerfile.frontend` instead of pulling an unpublished GHCR image.

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
