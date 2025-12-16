# Cloud-X Backend: Docker Deployment and Multi-Node Topology Plan

This document describes how to refactor the Flask backend for containerized deployment on any VPS, establish node visibility and health, and support load balancing. It focuses on a practical path you can complete incrementally within a couple of hours for the first pass.

## Goals
- Build and run the backend from a Docker image (Python base, no system Python assumptions).
- Standardize a service port and health/metrics endpoints.
- Allow multiple backend nodes to register and be visible to a primary node (control plane) for status and simple load distribution.
- Make it easy to push updates to remote Ubuntu nodes (pull new image and restart via Docker Compose).
- Keep this minimally invasive for the current codebase; start with docs and a compose template.

## Proposed Container Baseline
- Base image: `python:3.10-slim` (or 3.11-slim if compatible with deps).
- Working directory: `/app`
- Install system deps: `build-essential` (for pip builds), `nmap`, `zmap`, `masscan` (optional; can be installed on host and mounted in if root requirements block container).
- Copy backend code: `cloudx-flask-backend/`
- Install Python deps: `pip install -r requirements.txt`
- Entrypoint (MVP): `gunicorn -w 4 -k gevent -b 0.0.0.0:5001 app:app`
- Volumes (optional):
  - `/data/cloudx` for SQLite or logs (prefer external DB for multi-node).
  - `/scripts` if you want to share the agent installer scripts as static content.

## Ports and Endpoints
- Service API: `5001` (HTTP). Keep aligned with current default to minimize code changes.
- Health: `GET /api/health` (already exists).
- Ping: `GET /api/ping` (already exists).
- Node heartbeat (new, suggested): `POST /api/nodes/heartbeat` to let workers report liveness to the primary.
- Metrics (optional, suggested): `GET /metrics` (Prometheus text), or reuse `/api/system-monitor?target=localhost` internally for basic stats.

## Node Topology (Control + Workers)
- **Primary node**: runs API and a registry of nodes (in DB). Provides an endpoint for registration/heartbeat and a “nodes” list for visibility.
- **Worker nodes**: run the same container image; on startup, call the primary to register. They share the same backing datastore (Redis/Postgres) so task state is consistent.
- **Shared state** (recommended):
  - Postgres for durable data (instead of SQLite).
  - Redis for Celery (if/when you add workers for scans/tasks).
- **Load balancing**: place Nginx/HAProxy/Traefik in front of multiple backend containers. Nginx listens on `80/443`, proxies to the backend pool on `5001`.

## Minimal API Additions (future code changes)
- `POST /api/nodes/register`: body `{node_id, hostname, ip, role, capabilities, version}`.
- `POST /api/nodes/heartbeat`: body `{node_id, status, cpu, mem, loadavg, updated_at}`.
- `GET /api/nodes`: list nodes and their last heartbeat (for UI visibility).
- `GET /api/nodes/:id`: detail view (optional).

For a first doc-only pass, do not change code; add these endpoints later behind auth.

## Docker Compose Template (per VPS)

Create `docker-compose.yml` on the target VPS:
```yaml
version: "3.8"
services:
  backend:
    image: ghcr.io/your-org/cloudx-backend:latest
    restart: unless-stopped
    env_file:
      - .env
    ports:
      - "5001:5001"
    volumes:
      - ./data:/data/cloudx  # if using SQLite or local artifacts
    depends_on:
      - redis
      # - postgres  # if/when you move off SQLite

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    ports:
      - "6379:6379"

  # postgres:
  #   image: postgres:16-alpine
  #   restart: unless-stopped
  #   environment:
  #     POSTGRES_USER: cloudx
  #     POSTGRES_PASSWORD: change_me
  #     POSTGRES_DB: cloudx
  #   volumes:
  #     - ./pgdata:/var/lib/postgresql/data
  #   ports:
  #     - "5432:5432"
```

Example `.env` (MVP):
```
FLASK_DEBUG=0
DATABASE_URL=sqlite:////data/cloudx/scans.db
PORT=5001
PRIMARY_NODE_URL=http://primary-node:5001
NODE_ID=$(hostname)
```

### Building and Publishing the Image
Locally (or in CI):
```
docker build -t ghcr.io/your-org/cloudx-backend:latest -f Dockerfile .
docker push ghcr.io/your-org/cloudx-backend:latest
```
If you do not have a registry, scp the built image tarball:
```
docker save ghcr.io/your-org/cloudx-backend:latest > cloudx-backend.tar
scp cloudx-backend.tar user@vps:/tmp
ssh user@vps "docker load -i /tmp/cloudx-backend.tar"
```

### Deploy/Update on Ubuntu VPS
```
ssh user@vps
cd /opt/cloudx
docker compose pull          # or docker compose build if building on-box
docker compose up -d
```
Automate with a systemd unit + timer or a cron job that does `docker compose pull && docker compose up -d`.

### Registry Auth
- Use GitHub Container Registry (GHCR) or Docker Hub.
- Log in once per node:
  `echo $CR_PAT | docker login ghcr.io -u USERNAME --password-stdin`

## Load Balancing and Visibility
- Put Nginx/Traefik in front of two or more backend containers:
  - Upstream: `backend1:5001`, `backend2:5001`.
  - Health check: `/api/health` every 5s.
- Node list page (future UI): fetch `/api/nodes` to show status, last_seen, version.
- Metrics: expose Prometheus metrics via a small `/metrics` endpoint or sidecar (Node exporter if you prefer host metrics).

## Feasibility and Suggested Order (under 2 hours for docs + scaffolding)
1) **Docs (this file) + sample Dockerfile and compose** (no code changes yet).
2) Add a `Dockerfile` and `docker-compose.yml` to the repo (single-container mode first).
3) Add a simple `NODE_ID` env and `PRIMARY_NODE_URL` placeholder in config.
4) Later: implement `/api/nodes/register` and `/api/nodes/heartbeat` to populate a `nodes` table.
5) Add Nginx reverse proxy config (optional, after two nodes exist).
6) Add CI to build and push `ghcr.io/.../cloudx-backend:latest` on `main`.

## Risks and Notes
- Scanners (nmap/zmap/masscan) may need raw socket access; container must run with `--cap-add=NET_RAW` or on host network, or install scanners on host and mount in if needed.
- SQLite is not multi-node friendly; move to Postgres before serious multi-node use.
- Ensure auth before exposing node registration/heartbeat endpoints (Clerk JWT validation on backend).
- Keep secrets out of images; rely on env vars or Docker secrets.
