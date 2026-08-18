#!/bin/sh
set -eu

bundle_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$bundle_dir"

"$bundle_dir/scripts/verify.sh"
docker compose --env-file .env -f compose.yaml pull
docker compose --env-file .env -f compose.yaml up -d
docker compose --env-file .env -f compose.yaml ps
