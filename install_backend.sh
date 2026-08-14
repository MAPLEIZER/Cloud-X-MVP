#!/usr/bin/env bash
set -euo pipefail
umask 077

prompt() {
  local var="$1" default="$2" msg="$3" input
  read -r -p "$msg [$default]: " input
  printf -v "$var" '%s' "${input:-$default}"
}

compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    echo "docker compose"
  elif command -v docker-compose >/dev/null 2>&1; then
    echo "docker-compose"
  else
    echo ""
  fi
}

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Required environment variable $name is not set." >&2
    exit 1
  fi
}

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required." >&2
  exit 1
fi

COMPOSE_BIN="$(compose_cmd)"
if [[ -z "$COMPOSE_BIN" ]]; then
  echo "docker compose is required." >&2
  exit 1
fi

# Authentication is deliberately fail-closed. Export these before running:
#   CLERK_SECRET_KEY
#   CLERK_AUTHORIZED_PARTIES
#   CLERK_ALLOWED_USER_IDS
require_env CLERK_SECRET_KEY
require_env CLERK_AUTHORIZED_PARTIES
require_env CLERK_ALLOWED_USER_IDS

# Remote deployment is separately fail-closed. An empty JSON object means the
# API can run but no host is authorized for remote agent deployment.
DEPLOYMENT_TARGET_ALLOWLIST_JSON="${DEPLOYMENT_TARGET_ALLOWLIST_JSON:-{}}"
ENABLE_WINDOWS_AGENT_DEPLOYMENT="${ENABLE_WINDOWS_AGENT_DEPLOYMENT:-false}"

prompt DATA_DIR "/opt/cloudx-backend" "Where should data/config live"
prompt IMAGE "cloudx-backend:latest" "Docker image to run"
prompt HOST_PORT "5001" "Host port to expose the API on"
prompt NODE_ROLE "primary" "Node role (primary/worker)"
prompt NODE_ID "$(hostname -s)" "Node ID to persist"

if ! [[ "$HOST_PORT" =~ ^[0-9]+$ ]] || (( HOST_PORT < 1 || HOST_PORT > 65535 )); then
  echo "HOST_PORT must be between 1 and 65535." >&2
  exit 1
fi
if [[ "$NODE_ROLE" != "primary" && "$NODE_ROLE" != "worker" ]]; then
  echo "NODE_ROLE must be primary or worker." >&2
  exit 1
fi
if ! [[ "$ENABLE_WINDOWS_AGENT_DEPLOYMENT" =~ ^(true|false|1|0|yes|no|on|off)$ ]]; then
  echo "ENABLE_WINDOWS_AGENT_DEPLOYMENT must be a boolean value." >&2
  exit 1
fi

# Validate the deployment allow-list before writing configuration. The backend
# performs the same validation again on startup.
python3 - "$DEPLOYMENT_TARGET_ALLOWLIST_JSON" <<'PY'
import ipaddress
import json
import re
import sys

principal_re = re.compile(r"^(?:user|org):[A-Za-z0-9_-]{1,128}$")
host_label_re = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")

try:
    value = json.loads(sys.argv[1])
except json.JSONDecodeError as exc:
    raise SystemExit(f"Invalid DEPLOYMENT_TARGET_ALLOWLIST_JSON: {exc}")
if not isinstance(value, dict):
    raise SystemExit("DEPLOYMENT_TARGET_ALLOWLIST_JSON must be a JSON object")

for principal, entries in value.items():
    if not isinstance(principal, str) or not principal_re.fullmatch(principal):
        raise SystemExit(f"Invalid deployment principal: {principal!r}")
    if not isinstance(entries, list):
        raise SystemExit(f"Targets for {principal!r} must be a list")
    for entry in entries:
        if not isinstance(entry, str) or not entry or entry != entry.strip():
            raise SystemExit(f"Invalid deployment target: {entry!r}")
        try:
            if "/" in entry:
                ipaddress.ip_network(entry, strict=False)
            else:
                ipaddress.ip_address(entry)
        except ValueError:
            host = entry[:-1] if entry.endswith(".") else entry
            labels = host.split(".")
            if not host or len(host) > 253 or not all(host_label_re.fullmatch(label) for label in labels):
                raise SystemExit(f"Invalid deployment target: {entry!r}")
PY

POSTGRES_DB="${POSTGRES_DB:-cloudx}"
POSTGRES_USER="${POSTGRES_USER:-cloudx}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')}"

if ! [[ "$POSTGRES_DB" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "POSTGRES_DB may contain only letters, digits, and underscores." >&2
  exit 1
fi
if ! [[ "$POSTGRES_USER" =~ ^[A-Za-z0-9_]+$ ]]; then
  echo "POSTGRES_USER may contain only letters, digits, and underscores." >&2
  exit 1
fi

DATABASE_URL="$(python3 - "$POSTGRES_USER" "$POSTGRES_PASSWORD" "$POSTGRES_DB" <<'PY'
import sys
from urllib.parse import quote

user, password, database = sys.argv[1:4]
print(
    "postgresql+psycopg://"
    f"{quote(user, safe='')}:{quote(password, safe='')}@postgres:5432/"
    f"{quote(database, safe='')}"
)
PY
)"

HOSTNAME_RESOLVED="$(hostname -f 2>/dev/null || hostname -s 2>/dev/null || echo "127.0.0.1")"
PRIMARY_DEFAULT="http://${HOSTNAME_RESOLVED:-127.0.0.1}:5001"
if [[ "$NODE_ROLE" == "worker" ]]; then
  prompt PRIMARY_NODE_URL "$PRIMARY_DEFAULT" "Primary node URL"
else
  PRIMARY_NODE_URL="$PRIMARY_DEFAULT"
fi

prompt ADD_NET_RAW "y" "Add NET_RAW capability for scanners?"
prompt IMAGE_TAR "" "Optional path to a prebuilt image tarball to load"

install -d -m 0700 "$DATA_DIR"
cd "$DATA_DIR"

if [[ -n "$IMAGE_TAR" ]]; then
  docker load -i "$IMAGE_TAR"
elif [[ -n "$(docker images -q "$IMAGE" 2>/dev/null)" ]]; then
  echo "Using existing image: $IMAGE"
else
  docker pull "$IMAGE"
fi

cat > .env <<EOF
FLASK_ENV=production
PORT=5001
PRIMARY_NODE_URL=$PRIMARY_NODE_URL
NODE_ROLE=$NODE_ROLE
NODE_ID=$NODE_ID
CLERK_SECRET_KEY=$CLERK_SECRET_KEY
CLERK_AUTHORIZED_PARTIES=$CLERK_AUTHORIZED_PARTIES
CLERK_ALLOWED_USER_IDS=$CLERK_ALLOWED_USER_IDS
DEPLOYMENT_TARGET_ALLOWLIST_JSON=$DEPLOYMENT_TARGET_ALLOWLIST_JSON
ENABLE_WINDOWS_AGENT_DEPLOYMENT=$ENABLE_WINDOWS_AGENT_DEPLOYMENT
POSTGRES_DB=$POSTGRES_DB
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
DATABASE_URL=$DATABASE_URL
REDIS_URL=redis://redis:6379/0
MAX_CONCURRENT_SCANS=${MAX_CONCURRENT_SCANS:-4}
SCAN_WORKERS=${SCAN_WORKERS:-2}
GUNICORN_WORKERS=${GUNICORN_WORKERS:-2}
GUNICORN_THREADS=${GUNICORN_THREADS:-4}
GUNICORN_TIMEOUT=${GUNICORN_TIMEOUT:-300}
EOF
chmod 0600 .env

CAP_RAW_BLOCK=$'    cap_add: []'
if [[ "$ADD_NET_RAW" =~ ^[Yy]$ ]]; then
  CAP_RAW_BLOCK=$'    cap_add:\n      - NET_RAW'
fi

cat > docker-compose.yml <<EOF
services:
  postgres:
    image: postgres:17-alpine
    container_name: cloudx-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: \${POSTGRES_DB}
      POSTGRES_USER: \${POSTGRES_USER}
      POSTGRES_PASSWORD: \${POSTGRES_PASSWORD}
    volumes:
      - cloudx_postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U \$\${POSTGRES_USER} -d \$\${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 12

  redis:
    image: redis:8-alpine
    container_name: cloudx-redis
    command: ["redis-server", "--appendonly", "yes", "--appendfsync", "everysec"]
    restart: unless-stopped
    volumes:
      - cloudx_redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 12

  backend:
    image: $IMAGE
    container_name: cloudx-backend
    restart: unless-stopped
    ports:
      - "$HOST_PORT:5001"
    env_file:
      - .env
    environment:
      IDENTITY_FILE: /data/server_identity.json
    volumes:
      - cloudx_data:/data
    cap_drop:
      - ALL
$CAP_RAW_BLOCK
    security_opt:
      - no-new-privileges:true
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://127.0.0.1:5001/api/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s

  scan-worker:
    image: $IMAGE
    restart: unless-stopped
    env_file:
      - .env
    entrypoint: ["rq"]
    command: ["worker-pool", "scans", "--num-workers", "\${SCAN_WORKERS}", "--url", "\${REDIS_URL}", "--serializer", "json", "--worker-class", "scan_jobs.CloudXWorker"]
    cap_drop:
      - ALL
$CAP_RAW_BLOCK
    security_opt:
      - no-new-privileges:true
    depends_on:
      backend:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  cloudx_data:
  cloudx_postgres_data:
  cloudx_redis_data:
EOF
chmod 0600 docker-compose.yml

$COMPOSE_BIN up -d
echo "Deployment finished. PostgreSQL credentials are stored in $DATA_DIR/.env (mode 0600)."
echo "Redis is internal-only in this Compose topology and persists its AOF in a named volume."
if [[ "$DEPLOYMENT_TARGET_ALLOWLIST_JSON" == "{}" ]]; then
  echo "Remote agent deployment is fail-closed: no deployment targets are currently authorized."
fi
echo "Check health: curl -fsSL http://localhost:$HOST_PORT/api/health"
