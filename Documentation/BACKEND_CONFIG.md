# Cloud-X Backend Configuration

This document describes the current Flask backend configuration for the Cloud-X Security Dashboard.

## Core technologies

| Technology | Purpose |
|---|---|
| **Flask** | REST API |
| **Flask-SQLAlchemy / SQLAlchemy** | ORM and database access |
| **PostgreSQL** | Durable application and scan-state datastore |
| **Alembic** | Versioned database schema migrations |
| **Redis + RQ** | Durable scan queue, cancellation coordination and worker execution |
| **Gunicorn** | Production WSGI server |
| **Paramiko** | SSH deployment for Linux/macOS agents |
| **pywinrm** | Optional WinRM deployment for Windows agents |
| **psutil** | Local system metrics |
| **Nmap / ZMap / Masscan** | Network scanning engines |

The container runs as an unprivileged user. Writable runtime state is kept under `/data`; application source under `/app` is not writable by the runtime user.

## Required environment variables

Copy `cloudx-flask-backend/.env.example` to `.env` and replace every placeholder before starting the stack.

```env
CLERK_SECRET_KEY=sk_test_replace_me
CLERK_AUTHORIZED_PARTIES=http://localhost:5173
CLERK_ALLOWED_USER_IDS=user_replace_me

DEPLOYMENT_TARGET_ALLOWLIST_JSON={"user:user_replace_me":["192.168.1.0/24","server.example.com"]}
ENABLE_WINDOWS_AGENT_DEPLOYMENT=false

POSTGRES_DB=cloudx
POSTGRES_USER=cloudx
POSTGRES_PASSWORD=replace_with_a_long_random_password
DATABASE_URL=postgresql+psycopg://cloudx:replace_with_a_long_random_password@postgres:5432/cloudx

REDIS_URL=redis://redis:6379/0
MAX_CONCURRENT_SCANS=4
SCAN_WORKERS=2
GUNICORN_WORKERS=2
GUNICORN_THREADS=4
GUNICORN_TIMEOUT=300
```

`DATABASE_URL` is mandatory. The backend deliberately fails closed when no PostgreSQL connection URL is configured. If the username, password, or database contains reserved URL characters, URL-encode those values before constructing `DATABASE_URL`.

`REDIS_URL` is also required for API startup because scan submission is durable only when the queue is reachable. The checked-in Compose topology keeps Redis internal to the Docker network and enables append-only persistence. If an external Redis service is used, prefer authenticated TLS (`rediss://`) and network-level access controls.

## Remote deployment authorization

Remote agent deployment is additionally restricted by `DEPLOYMENT_TARGET_ALLOWLIST_JSON`. An empty or missing allow-list authorizes **no** remote deployment targets.

The JSON object is keyed by Clerk principals:

```json
{
  "user:user_123": ["10.20.30.0/24", "server.example.com"],
  "org:org_456": ["192.0.2.50", "2001:db8::/64"]
}
```

Rules:

- a `user:<Clerk user id>` entry authorizes targets for that user;
- an `org:<Clerk organization id>` entry authorizes targets when that organization is active in the authenticated session;
- IP/CIDR entries match literal IP targets;
- hostnames are exact, case-insensitive entries and are not resolved into CIDRs for authorization;
- there is no wildcard principal or wildcard host rule;
- invalid JSON, principals, hosts, or networks fail application startup rather than widening access.

Linux/macOS deployment arguments are shell-quoted before remote execution. The Windows path decodes validated values into PowerShell variables and passes those variables through PowerShell parameter binding; user values are not inserted directly into the PowerShell program.

Windows agent deployment is disabled by default. Set `ENABLE_WINDOWS_AGENT_DEPLOYMENT=true` only after WinRM connectivity, encryption and installer behavior have been validated in the target environment. The endpoint returns `503` for Windows requests while the flag is disabled.

The backend never logs submitted deployment passwords. Prefer scoped/ephemeral credentials or key-based SSH authentication when the deployment architecture is expanded beyond the current prototype.

## Database and migrations

Cloud-X no longer creates its production schema with `db.create_all()` and no longer uses `scans.db` as the application datastore. Database changes are versioned in `cloudx-flask-backend/migrations/` and applied with Alembic.

The queue-state migration adds `updated_at` to the scan record and makes `queued` the database default for new work. PostgreSQL is the source of truth for API-visible scan status, progress and results; Redis/RQ owns queue/control metadata and worker dispatch.

Apply migrations manually when needed:

```bash
cd cloudx-flask-backend
alembic upgrade head
```

Container startup also runs `alembic upgrade head` before Gunicorn starts. If PostgreSQL is unavailable or a migration fails, startup fails rather than serving against an unknown schema.

Useful migration commands:

```bash
alembic current
alembic history
alembic upgrade head
```

New schema changes should be represented by a reviewed migration file rather than runtime `create_all()` calls.

## Durable scan queue

Scan execution no longer runs in Flask background threads and the API process does not retain scanner `Popen` handles.

The lifecycle is:

1. an authenticated API request validates the scan parameters;
2. a Redis distributed lock serializes the global capacity check across multiple API workers/instances;
3. the API creates a PostgreSQL `Scan` row with a stable UUID job ID and enqueues the same ID into the RQ `scans` queue using the JSON serializer;
4. an isolated RQ worker owns the Nmap/ZMap/Masscan subprocess and writes progress/results back to PostgreSQL;
5. queued cancellation uses RQ job cancellation; a running scan receives a short-lived Redis cancellation marker that the scanner loop checks and uses to terminate its own subprocess cleanly;
6. API startup and individual status reads reconcile active PostgreSQL rows against RQ state instead of treating an API restart as a scan failure.

Because scanner state is outside Gunicorn, `GUNICORN_WORKERS` can be greater than one. Scale scan execution separately with `SCAN_WORKERS`. `MAX_CONCURRENT_SCANS` remains the API admission bound and is checked while holding the Redis enqueue lock.

The checked-in RQ worker uses JSON serialization instead of RQ's pickle default. Queue and worker configuration must continue to use the same serializer.

If Redis is unavailable, new scan submission/stop/delete operations that require queue coordination fail with `503`; the API does not silently fall back to in-process execution.

Worker containers are restartable. RQ queue metadata is persisted by Redis AOF, PostgreSQL retains user-visible scan state, and the custom worker termination handler records an unexpected work-horse death as a failed scan. Graceful worker shutdown lets the current work horse finish before the worker exits; cooperative scan cancellation is preferred to forcibly killing the work horse so external scanner subprocesses are not orphaned.

## Docker setup

From the repository root:

```bash
cd cloudx-flask-backend
cp .env.example .env
# Edit .env and replace all placeholder credentials and deployment principals.
docker compose build
docker compose up -d
docker compose ps
curl -fsS http://127.0.0.1:5001/api/health
```

The backend Compose stack includes PostgreSQL 17, persistent Redis and an isolated RQ scan-worker pool. The API waits for both PostgreSQL and Redis health. Backend and worker containers drop all Linux capabilities and add back only `NET_RAW` for scanner functionality, with `no-new-privileges` enabled.

## Standalone installer

`install_backend.sh` is an experimental bootstrap utility. It deploys the same PostgreSQL + Redis + RQ topology and stores generated PostgreSQL credentials in its local `.env` file with mode `0600`. Redis is internal-only in the generated Compose file and persists its AOF to a named volume. The installer no longer creates or bind-mounts a SQLite database.

For a production release, use immutable versioned images and a managed secret store rather than long-lived plaintext environment files.

## Agent deployment scripts

Agent deployment assets are stored under:

```text
cloudx-flask-backend/scripts/
├── windows/
│   ├── cloudx-agent-installer.psm1
│   ├── cloudx-agent-setup.ps1
│   ├── cloudx-agent-uninstaller.psm1
│   └── remove-threat.py
├── linux/
│   ├── cloudx-agent-install.sh
│   ├── cloudx-agent-setup.sh
│   └── remove-threat.py
└── mac/
    ├── cloudx-agent-install.sh
    └── cloudx-agent-setup.sh
```

The previous locally trusted code-signing certificate is no longer part of the current tree.
