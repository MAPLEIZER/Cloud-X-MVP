#!/bin/sh
set -eu

bundle_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$bundle_dir"

[ -f .env ] || {
  echo "Missing $bundle_dir/.env; copy .env.example and configure it first." >&2
  exit 1
}

sha256sum -c SHA256SUMS

python3 - "$bundle_dir/manifests/release.json" <<'PY'
import json
import re
import sys

manifest = json.load(open(sys.argv[1], encoding="utf-8"))
digest_ref = re.compile(r"^.+@sha256:[0-9a-f]{64}$")
for name, ref in manifest["images"].items():
    if not digest_ref.fullmatch(ref):
        raise SystemExit(f"{name} image is not digest-pinned: {ref}")
print(f"release manifest verified: {manifest['version']} @ {manifest['source']['commit'][:12]}")
PY

docker compose --env-file .env -f compose.yaml config >/dev/null
echo "Compose configuration verified."

if [ "${CLOUDX_VERIFY_LIVE:-false}" = "true" ]; then
  origin=${CLOUDX_VERIFY_ORIGIN:?CLOUDX_VERIFY_ORIGIN must be set when CLOUDX_VERIFY_LIVE=true}
  curl --fail --silent --show-error --location \
    --max-time 15 "$origin/_health/ready" >/dev/null
  echo "Live readiness verified at $origin."
fi
