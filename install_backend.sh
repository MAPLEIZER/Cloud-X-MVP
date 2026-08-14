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
POSTGRES_DB=$POSTGRES_DB
POSTGRES_USER=$POSTGRES_USER
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
DATABASE_URL=$DATABASE_URL
MAX_CONCURRENT_SCANS=${MAX_CONCURRENT_SCANS:-4}
GUNICORN_THREADS=${GUNICORN_THREADS:-8}
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
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://127.0.0.1:5001/api/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 20s

volumes:
  cloudx_data:
  cloudx_postgres_data:
EOF
chmod 0600 docker-compose.yml

$COMPOSE_BIN up -d
echo "Deployment finished. PostgreSQL credentials are stored in $DATA_DIR/.env (mode 0600)."
echo "Check health: curl -fsSL http://localhost:$HOST_PORT/api/health"
