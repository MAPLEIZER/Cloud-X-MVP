#!/usr/bin/env bash
set -euo pipefail

banner() {
cat <<'BANNER'
                                                                                                    
                                                                                                    
                                               @@@@@                                                
                                            @@@      @@                                             
                                          @@             @@                                         
                                     @@@@@@         @@@@@@@@@@@                                     
                                    @@@           @@@         @@                                    
                                   @@           @@@  @@@@@@@@@ @@                                   
                                   @@ @       @@@  @@@       @ @@                                   
                                   @@ @@    @@@  @@@         @ @@                                   
                                    @@   @@    @@@            @@                                    
                                     @@@@@@@@@@@       @@@@@@@                                      
                                         @@@                                                        
                                                                                                    
                                    @@                     @@    @    @                             
                               @    @@   @@             @  @     @@  @                              
                             @@@@@@ @@ @@@@@@  @@  @@ @@@@@@       @@                               
                            @@      @@ @@   @@ @   @@ @    @      @ @@                              
                             @@@@@  @@ @@@@@@  @@@@@@ @@@@@@@    @   @@                             
                                                                                                    
                                                                                                    
                                                                                                    
BANNER
}

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

banner

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed. Install it first (e.g., curl -fsSL https://get.docker.com | sh)" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required for identity generation. Install it and retry." >&2
  exit 1
fi

COMPOSE_BIN="$(compose_cmd)"
if [[ -z "$COMPOSE_BIN" ]]; then
  echo "docker compose is required. Install docker-compose-plugin (or docker-compose) and retry." >&2
  exit 1
fi

prompt DATA_DIR "/opt/cloudx-backend" "Where should data/config live"
prompt IMAGE "ghcr.io/mapleizer/cloudx-backend:latest" "Docker image to run (pulled or loaded locally; GHCR owner must be lowercase)"
prompt HOST_PORT "5001" "Host port to expose the API on"
prompt NODE_ROLE "primary" "Node role (primary/worker)"
prompt NODE_ID "$(hostname -s)" "Node ID to persist (maps to server_identity.json)"

HOSTNAME_RESOLVED="$(hostname -f 2>/dev/null || hostname -s 2>/dev/null || echo "127.0.0.1")"
PRIMARY_DEFAULT="http://${HOSTNAME_RESOLVED:-127.0.0.1}:5001"
if [[ "$NODE_ROLE" == "worker" ]]; then
  prompt PRIMARY_NODE_URL "$PRIMARY_DEFAULT" "Primary node URL (workers only)"
else
  PRIMARY_NODE_URL="$PRIMARY_DEFAULT"
fi

prompt ADD_NET_RAW "y" "Add NET_RAW capability for scanners (recommended)?"
prompt IMAGE_TAR "" "Optional path to a prebuilt image tarball to load"

mkdir -p "$DATA_DIR"
cd "$DATA_DIR"

if [[ -n "$IMAGE_TAR" ]]; then
  docker load -i "$IMAGE_TAR"
elif [[ -n "$(docker images -q "$IMAGE" 2>/dev/null)" ]]; then
  echo "Using existing image: $IMAGE"
else
  if ! docker pull "$IMAGE"; then
    echo "Warning: Failed to pull $IMAGE. Ensure the image is available locally or the registry is accessible." >&2
    exit 1
  fi
fi

# Ensure bind targets exist as files to avoid mount type conflicts
touch scans.db

# Ensure server_identity.json is valid JSON with a server_id
python3 - <<'PY'
import json, uuid, datetime, os, sys
from datetime import timezone
path = "server_identity.json"
data = None
if os.path.exists(path):
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception:
        data = None
if not data or "server_id" not in data:
    data = {
        "server_id": str(uuid.uuid4()),
        "created_at": datetime.datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    with open(path, "w") as f:
        json.dump(data, f)
PY

cat > .env <<EOF
FLASK_ENV=production
PORT=5001
PRIMARY_NODE_URL=$PRIMARY_NODE_URL
NODE_ROLE=$NODE_ROLE
NODE_ID=$NODE_ID
EOF

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
$CAP_RAW_BLOCK
EOF

$COMPOSE_BIN up -d
echo "Deployment finished. Check health: curl -fsSL http://localhost:$HOST_PORT/api/health"
