# GitHub Docker Builds (CI) and GHCR Images

This repo uses GitHub Actions to build Docker images and (for `main`) publish them to GitHub Container Registry (GHCR). This gives you reproducible, versioned images that servers can pull without building from source.

## Workflows at a glance

### `.github/workflows/backend-image.yml` (publish backend)
Runs on:
- Pushes to `main` that touch `cloudx-flask-backend/**` or the workflow file itself
- Manual runs via `workflow_dispatch`

What it does:
1. Checks out the repo.
2. Computes the GHCR namespace as lowercase `GITHUB_REPOSITORY_OWNER` (GHCR requires lowercase).
3. Sets up Docker Buildx (enables BuildKit features and caching).
4. Logs in to `ghcr.io` using `secrets.GHCR_TOKEN`.
5. Builds `./cloudx-flask-backend/Dockerfile` with context `./cloudx-flask-backend`.
6. Pushes two tags:
   - `ghcr.io/<owner>/cloudx-backend:latest`
   - `ghcr.io/<owner>/cloudx-backend:<git-sha>`
7. Uses GitHub Actions cache (`type=gha`) to speed up future builds.

### `.github/workflows/frontend-image.yml` (publish frontend)
Runs on:
- Pushes to `main` that touch frontend-related files (`src/**`, `public/**`, `Dockerfile.frontend`, lockfiles, etc.)
- Manual runs via `workflow_dispatch`

What it does (same pattern as backend):
- Builds and pushes:
  - `ghcr.io/<owner>/cloudx-frontend:latest`
  - `ghcr.io/<owner>/cloudx-frontend:<git-sha>`
- Passes a build arg `FRONTEND_API_BASE_URL` (defaults to `http://localhost:5001`), so the frontend image can bake in the API base URL at build time.

### `.github/workflows/docker-build.yml` (PR/branch build checks)
Runs on:
- Pushes to `main`
- All pull requests

What it does:
- Builds both images using Buildx (and sets up QEMU), but does **not** push to GHCR.
- Uses `load: true` so the built image is loaded into the runner’s local Docker engine (useful for later steps, though this workflow currently only builds).
- Tags locally as `frontend:latest` and `backend:latest`.

## Why this helps

- Faster deploys: servers can run `docker compose pull` to fetch a prebuilt image instead of building from source.
- Reproducibility: the exact image used can be pinned by SHA tag (`:<git-sha>`), making rollbacks and debugging easier than “whatever source was on the server”.
- Safer separation of concerns: CI builds once in a clean environment; runtime machines only pull and run.
- Speed via caching: `cache-from/cache-to: type=gha` reuses layers across workflow runs to reduce build time.

## How it ties into deployment in this repo

- `deploy/frontend/docker-compose.yml` uses `ghcr.io/mapleizer/cloudx-frontend:latest` (owner must be lowercase for GHCR).
- Backend deployments typically use a compose file on the server (the helper script assumes `/opt/cloudx-backend/docker-compose.yml`).
- `deploy/pull-frontend.sh` and `deploy/pull-backend.sh` perform:
  - `docker compose pull`
  - `docker compose up -d`
  - `docker compose ps`

## Requirements / gotchas

- `GHCR_TOKEN` secret must exist in the GitHub repo settings and have permission to push packages (commonly a PAT with `write:packages`, or `GITHUB_TOKEN` if configured appropriately).
- GHCR image names are lowercased by the workflow to avoid registry naming issues.
- The frontend API base URL is baked in at build time; changing it generally means publishing a new frontend image (or switching to a runtime-config approach).

## Quick usage

- Latest release-style tag: `ghcr.io/<owner>/cloudx-backend:latest` and `ghcr.io/<owner>/cloudx-frontend:latest`
- Exact build tag (recommended for pinning): `ghcr.io/<owner>/cloudx-backend:<git-sha>` and `ghcr.io/<owner>/cloudx-frontend:<git-sha>`
