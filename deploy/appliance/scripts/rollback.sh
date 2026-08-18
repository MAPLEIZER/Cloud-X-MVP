#!/bin/sh
set -eu

current_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
previous_file="$current_dir/.previous-release"

[ -f "$previous_file" ] || {
  echo "No previous release is recorded for this bundle." >&2
  exit 1
}

[ "${CLOUDX_ALLOW_SCHEMA_COMPATIBLE_ROLLBACK:-false}" = "true" ] || {
  echo "Rollback is blocked by default because Alembic migrations are not downgraded automatically." >&2
  echo "Set CLOUDX_ALLOW_SCHEMA_COMPATIBLE_ROLLBACK=true only after the target release documents schema compatibility." >&2
  exit 1
}

previous_dir=$(cat "$previous_file")
[ -d "$previous_dir" ] || {
  echo "Recorded previous bundle is unavailable: $previous_dir" >&2
  exit 1
}

if [ ! -f "$previous_dir/.env" ]; then
  cp "$current_dir/.env" "$previous_dir/.env"
fi

"$previous_dir/scripts/verify.sh"

cd "$previous_dir"
docker compose --env-file .env -f compose.yaml up -d
docker compose --env-file .env -f compose.yaml ps
