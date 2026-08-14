#!/bin/sh
set -eu

IDENTITY_FILE="${IDENTITY_FILE:-/data/server_identity.json}"

if [ ! -f "$IDENTITY_FILE" ]; then
    echo "Initializing new Cloud-X Backend Node..."
    SERVER_ID="$(python3 -c 'import uuid; print(uuid.uuid4())')"
    python3 - "$IDENTITY_FILE" "$SERVER_ID" <<'PY'
import datetime
import json
import sys
from datetime import timezone

path, server_id = sys.argv[1:3]
with open(path, "w", encoding="utf-8") as handle:
    json.dump(
        {
            "server_id": server_id,
            "created_at": datetime.datetime.now(timezone.utc).isoformat(),
        },
        handle,
    )
PY
    chmod 0600 "$IDENTITY_FILE"
else
    SERVER_ID="$(python3 - "$IDENTITY_FILE" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    print(json.load(handle)["server_id"])
PY
)"
fi

export SERVER_ID

# Database schema changes are explicit and versioned. Startup fails closed when
# the configured PostgreSQL database cannot be migrated.
alembic upgrade head

python3 - <<'PY'
from app import app, cleanup_stale_scans

with app.app_context():
    cleanup_stale_scans()
PY

exec gunicorn \
    --workers 1 \
    --threads "${GUNICORN_THREADS:-8}" \
    --bind "0.0.0.0:${PORT:-5001}" \
    --timeout "${GUNICORN_TIMEOUT:-300}" \
    --access-logfile - \
    --error-logfile - \
    app:app
