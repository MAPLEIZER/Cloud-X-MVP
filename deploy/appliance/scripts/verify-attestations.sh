#!/bin/sh
set -eu

bundle_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
manifest="$bundle_dir/manifests/release.json"

command -v gh >/dev/null 2>&1 || {
  echo "GitHub CLI (gh) is required for online attestation verification." >&2
  exit 1
}
command -v python3 >/dev/null 2>&1 || {
  echo "python3 is required to read the release manifest." >&2
  exit 1
}

read_manifest() {
  python3 - "$manifest" "$1" <<'PY'
import json
import sys
value = json.load(open(sys.argv[1], encoding="utf-8"))
for part in sys.argv[2].split('.'):
    value = value[part]
print(value)
PY
}

repository=$(read_manifest evidence.signature_policy.repository)
signer=$(read_manifest evidence.signature_policy.signer_workflow)
issuer=$(read_manifest evidence.signature_policy.oidc_issuer)
frontend=$(read_manifest images.frontend)
backend=$(read_manifest images.backend)

for image in "$frontend" "$backend"; do
  gh attestation verify "oci://$image" \
    --repo "$repository" \
    --signer-workflow "$signer" \
    --cert-oidc-issuer "$issuer"
done

echo "Cloud-X image provenance verified against repository and signer-workflow identity."
