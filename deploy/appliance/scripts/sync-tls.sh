#!/bin/sh
set -eu

bundle_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
env_file="$bundle_dir/.env"
source_cert=${1:-}
source_key=${2:-}

[ -f "$env_file" ] || { echo "Cloud-X .env is missing" >&2; exit 1; }
[ -n "$source_cert" ] && [ -n "$source_key" ] || {
  echo "Usage: $0 /path/to/source/fullchain.pem /path/to/source/privkey.pem" >&2
  exit 2
}

for command in python3 openssl sha256sum; do
  command -v "$command" >/dev/null 2>&1 || { echo "$command is required" >&2; exit 1; }
done

read_env() {
  python3 - "$env_file" "$1" <<'PY'
import sys
path, key = sys.argv[1:]
for raw in open(path, encoding="utf-8"):
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    current, value = line.split("=", 1)
    if current == key:
        print(value)
        raise SystemExit(0)
raise SystemExit(2)
PY
}

validate_pair() {
  cert=$1
  key=$2
  [ -r "$cert" ] && [ -r "$key" ] || return 1
  openssl x509 -in "$cert" -noout -checkend 86400 >/dev/null 2>&1 || return 1
  cert_pub=$(openssl x509 -in "$cert" -pubkey -noout | openssl pkey -pubin -outform DER 2>/dev/null | sha256sum | awk '{print $1}')
  key_pub=$(openssl pkey -in "$key" -pubout -outform DER 2>/dev/null | sha256sum | awk '{print $1}')
  [ -n "$cert_pub" ] && [ "$cert_pub" = "$key_pub" ]
}

validate_pair "$source_cert" "$source_key" || {
  echo "Source certificate/private key are invalid, mismatched, or expire within 24 hours" >&2
  exit 1
}

target_cert=$(read_env CLOUDX_TLS_CERT_FILE)
target_key=$(read_env CLOUDX_TLS_KEY_FILE)

mkdir -p "$(dirname "$target_cert")" "$(dirname "$target_key")"

same_path() {
  python3 - "$1" "$2" <<'PY'
import os
import sys
raise SystemExit(0 if os.path.realpath(sys.argv[1]) == os.path.realpath(sys.argv[2]) else 1)
PY
}

if ! same_path "$source_cert" "$target_cert"; then
  [ -e "$target_cert" ] || : >"$target_cert"
  cat "$source_cert" >"$target_cert"
fi
if ! same_path "$source_key" "$target_key"; then
  umask 077
  [ -e "$target_key" ] || : >"$target_key"
  cat "$source_key" >"$target_key"
fi
chmod 0644 "$target_cert"
chmod 0600 "$target_key"

validate_pair "$target_cert" "$target_key" || {
  echo "Refusing nginx reload because synchronized TLS material failed validation" >&2
  exit 1
}

if command -v docker >/dev/null 2>&1; then
  cd "$bundle_dir"
  if docker compose --env-file .env -f compose.yaml ps --status running -q reverse-proxy 2>/dev/null | grep -q .; then
    docker compose --env-file .env -f compose.yaml exec -T reverse-proxy nginx -t
    docker compose --env-file .env -f compose.yaml exec -T reverse-proxy nginx -s reload
  fi
fi

if [ -n "${CLOUDX_VERIFY_ORIGIN:-}" ] && command -v curl >/dev/null 2>&1; then
  curl --fail --silent --show-error --max-time 15 "${CLOUDX_VERIFY_ORIGIN%/}/_health/live" >/dev/null
fi

echo "Cloud-X TLS material synchronized and validated."
