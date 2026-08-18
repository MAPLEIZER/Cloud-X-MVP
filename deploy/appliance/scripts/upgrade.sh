#!/bin/sh
set -eu

current_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
new_dir=${1:-}

[ -n "$new_dir" ] || {
  echo "Usage: $0 /path/to/new/cloudx-appliance-vX.Y.Z" >&2
  exit 2
}
new_dir=$(CDPATH= cd -- "$new_dir" && pwd)

[ -f "$current_dir/.env" ] || {
  echo "Current bundle has no .env to carry forward." >&2
  exit 1
}
[ -f "$new_dir/.env.example" ] || {
  echo "Target is not a Cloud-X appliance bundle: $new_dir" >&2
  exit 1
}

cp "$current_dir/.env" "$new_dir/.env"
"$new_dir/scripts/verify.sh"

printf '%s\n' "$current_dir" >"$new_dir/.previous-release"

cd "$new_dir"
docker compose --env-file .env -f compose.yaml pull
docker compose --env-file .env -f compose.yaml run --rm --no-deps \
  --entrypoint alembic backend upgrade head
docker compose --env-file .env -f compose.yaml up -d
docker compose --env-file .env -f compose.yaml ps

echo "Upgrade applied. Previous bundle recorded in $new_dir/.previous-release."
