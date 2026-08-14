# Cloud-X Backend Configuration

This document describes the current Flask backend configuration for the Cloud-X Security Dashboard.

## Core technologies

| Technology | Purpose |
|---|---|
| **Flask** | REST API |
| **Flask-SQLAlchemy / SQLAlchemy** | ORM and database access |
| **PostgreSQL** | Durable backend datastore |
| **Alembic** | Versioned database schema migrations |
| **Gunicorn** | Production WSGI server |
| **Paramiko** | SSH deployment for Linux/macOS agents |
| **pywinrm** | WinRM deployment for Windows agents |
| **psutil** | Local system metrics |
| **Nmap / ZMap / Masscan** | Network scanning engines |

The container runs as an unprivileged user. Writable runtime state is kept under `/data`; application source under `/app` is not writable by the runtime user.

## Required environment variables

Copy `cloudx-flask-backend/.env.example` to `.env` and replace every placeholder before starting the stack.

```env
CLERK_SECRET_KEY=sk_test_replace_me
CLERK_AUTHORIZED_PARTIES=http://localhost:5173
CLERK_ALLOWED_USER_IDS=user_replace_me

POSTGRES_DB=cloudx
POSTGRES_USER=cloudx
POSTGRES_PASSWORD=replace_with_a_long_random_password
DATABASE_URL=postgresql+psycopg://cloudx:replace_with_a_long_random_password@postgres:5432/cloudx

MAX_CONCURRENT_SCANS=4
GUNICORN_THREADS=8
GUNICORN_TIMEOUT=300
```

`DATABASE_URL` is mandatory. The backend deliberately fails closed when no PostgreSQL connection URL is configured. If the username, password, or database contains reserved URL characters, URL-encode those values before constructing `DATABASE_URL`.

## Database and migrations

Cloud-X no longer creates its production schema with `db.create_all()` and no longer uses `scans.db` as the application datastore. Database changes are versioned in `cloudx-flask-backend/migrations/` and applied with Alembic.

The initial migration creates the `scan` table used for scan status and results.

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

## Docker setup

From the repository root:

```bash
cd cloudx-flask-backend
cp .env.example .env
# Edit .env and replace all placeholder credentials.
docker compose build
docker compose up -d
docker compose ps
curl -fsS http://127.0.0.1:5001/api/health
```

The backend Compose stack includes PostgreSQL 17 with a persistent named volume. The API waits for PostgreSQL health before starting. The backend drops all Linux capabilities and adds back only `NET_RAW` for scanner functionality, with `no-new-privileges` enabled.

## Standalone installer

`install_backend.sh` is an experimental bootstrap utility. It now deploys the same PostgreSQL-backed topology and stores generated PostgreSQL credentials in its local `.env` file with mode `0600`. It does not create or bind-mount a SQLite database.

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

## Scan execution limitation

Scan processes still run in local background threads and active process handles remain in memory. Gunicorn therefore remains configured as a single worker with multiple threads. Moving scans to a durable queue is tracked separately in issue #25.
