#!/bin/sh
set -eu

bundle_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
env_file="$bundle_dir/.env"

fail() {
  echo "Cloud-X host preflight failed: $*" >&2
  exit 1
}

[ -f "$env_file" ] || fail "copy .env.example to .env and configure it first"

for command in python3 docker openssl sha256sum; do
  command -v "$command" >/dev/null 2>&1 || fail "$command is required"
done
docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 plugin is required"
docker info >/dev/null 2>&1 || fail "Docker daemon is unavailable to the current user"

python3 - "$env_file" <<'PY'
import os
import stat
import sys
path = sys.argv[1]
mode = stat.S_IMODE(os.stat(path).st_mode)
if mode & 0o077:
    raise SystemExit(f"{path} contains secrets and must not be group/world accessible; current mode is {mode:03o}")
PY

arch=$(uname -m)
[ "$arch" = "x86_64" ] || fail "validated Phase 1 host architecture is x86_64, found $arch"

if [ -r /etc/os-release ]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  if [ "${ID:-}" != "ubuntu" ] || [ "${VERSION_ID:-}" != "24.04" ]; then
    [ "${CLOUDX_ALLOW_UNVALIDATED_HOST:-false}" = "true" ] || \
      fail "validated pilot OS is Ubuntu 24.04 LTS; set CLOUDX_ALLOW_UNVALIDATED_HOST=true only for unsupported testing"
  fi
else
  fail "/etc/os-release is unavailable"
fi

cpus=$(getconf _NPROCESSORS_ONLN 2>/dev/null || true)
[ -n "$cpus" ] || cpus=$(nproc 2>/dev/null || echo 0)
[ "$cpus" -ge 4 ] || fail "pilot support floor is 4 vCPU; found $cpus"

memory_kib=$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)
[ "$memory_kib" -ge 7340032 ] || fail "pilot support floor is approximately 8 GiB RAM"

disk_path=/
[ -d /var/lib/docker ] && disk_path=/var/lib/docker
free_kib=$(df -Pk "$disk_path" | awk 'NR==2 {print $4}')
[ "$free_kib" -ge 41943040 ] || fail "at least 40 GiB free space is required on $disk_path"

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

python3 - "$env_file" <<'PY'
import sys
required = {
    "POSTGRES_PASSWORD",
    "DATABASE_URL",
    "CLOUDX_PUBLIC_HOSTNAME",
    "CLERK_PUBLISHABLE_KEY",
    "CLERK_JWT_KEY",
    "CLERK_AUTHORIZED_PARTIES",
    "CLERK_ALLOWED_USER_IDS",
    "WAZUH_API_URL",
    "WAZUH_API_USERNAME",
    "WAZUH_API_PASSWORD",
    "WAZUH_INDEXER_URL",
    "WAZUH_INDEXER_USERNAME",
    "WAZUH_INDEXER_PASSWORD",
    "CLOUDX_TLS_CERT_FILE",
    "CLOUDX_TLS_KEY_FILE",
}
values = {}
for raw in open(sys.argv[1], encoding="utf-8"):
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    values[key] = value
missing = sorted(key for key in required if not values.get(key))
if missing:
    raise SystemExit("missing required .env values: " + ", ".join(missing))
placeholder_tokens = ("replace_", "replace-with", "example.com", "user_replace", "...")
unsafe = sorted(
    key for key in required
    if any(token in values.get(key, "").lower() for token in placeholder_tokens)
)
if unsafe:
    raise SystemExit("placeholder values remain in .env: " + ", ".join(unsafe))
PY

hostname=$(read_env CLOUDX_PUBLIC_HOSTNAME)
cert_file=$(read_env CLOUDX_TLS_CERT_FILE)
key_file=$(read_env CLOUDX_TLS_KEY_FILE)

[ -r "$cert_file" ] || fail "TLS certificate is unreadable: $cert_file"
[ -r "$key_file" ] || fail "TLS private key is unreadable: $key_file"
openssl x509 -in "$cert_file" -noout -checkend 86400 >/dev/null 2>&1 || \
  fail "TLS certificate is invalid or expires within 24 hours"

cert_pub=$(openssl x509 -in "$cert_file" -pubkey -noout | openssl pkey -pubin -outform DER 2>/dev/null | sha256sum | awk '{print $1}')
key_pub=$(openssl pkey -in "$key_file" -pubout -outform DER 2>/dev/null | sha256sum | awk '{print $1}')
[ -n "$cert_pub" ] && [ "$cert_pub" = "$key_pub" ] || fail "TLS certificate and private key do not match"

if command -v getent >/dev/null 2>&1; then
  getent ahosts "$hostname" >/dev/null 2>&1 || fail "public hostname does not resolve: $hostname"
fi

cd "$bundle_dir"
docker compose --env-file .env -f compose.yaml config >/dev/null

echo "Cloud-X host preflight passed: Ubuntu 24.04 x86_64, resource floor, Docker/Compose, secret-file permissions, DNS, TLS pair and Compose configuration."
