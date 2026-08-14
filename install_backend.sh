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
  echo "python3 is required for identity generation." >&2
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

touch scans.db
chmod 0600 scans.db

python3 - <<'PY'
import datetime
import json
import os
import uuid
from datetime import timezone

path = "server_identity.json"
data = None
if os.path.exists(path):
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        data = None

if not data or "server_id" not in data:
    data = {
        "server_id": str(uuid.uuid4()),
        "created_at": datetime.datetime.now(timezone.utc).isoformat(),
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle)

os.chmod(path, 0o600)
PY

cat > .env <<EOF
FLASK_ENV=production
PORT=5001
DATABASE_PATH=/app/scans.db
PRIMARY_NODE_URL=$PRIMARY_NODE_URL
NODE_ROLE=$NODE_ROLE
NODE_ID=$NODE_ID
CLERK_SECRET_KEY=$CLERK_SECRET_KEY
CLERK_AUTHORIZED_PARTIES=$CLERK_AUTHORIZED_PARTIES
CLERK_ALLOWED_USER_IDS=$CLERK_ALLOWED_USER_IDS
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
  backend:
    image: $IMAGE
    container_name: cloudx-backend
    restart: unless-stopped
    ports:
      - "$HOST_PORT:5001"
    env_file:
      - .env
    volumes:
      - "${DATA_DIR}/scans.db:/app/scans.db"
      - "${DATA_DIR}/server_identity.json:/app/server_identity.json"
    cap_drop:
      - ALL
$CAP_RAW_BLOCK
    security_opt:
      - no-new-privileges:true
EOF
chmod 0600 docker-compose.yml

$COMPOSE_BIN up -d
echo "Deployment finished. Check health: curl -fsSL http://localhost:$HOST_PORT/api/health"
