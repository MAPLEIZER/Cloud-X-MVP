#!/bin/sh
set -eu

output=/usr/share/nginx/html/cloudx-config.js
api_base=${CLOUDX_API_BASE_URL:-}
clerk_key=${CLERK_PUBLISHABLE_KEY:-}

fail() {
  echo "Cloud-X frontend runtime configuration: $*" >&2
  exit 1
}

case "$api_base" in
  ""|/*|http://*|https://*) ;;
  *) fail "CLOUDX_API_BASE_URL must be empty, root-relative, http://, or https://" ;;
esac

if [ -n "$api_base" ] && ! printf '%s' "$api_base" | grep -Eq '^[A-Za-z0-9:/?&=#._~%+@!-]+$'; then
  fail "CLOUDX_API_BASE_URL contains unsupported characters"
fi

[ -n "$clerk_key" ] || fail "CLERK_PUBLISHABLE_KEY must be set"
if ! printf '%s' "$clerk_key" | grep -Eq '^pk_[A-Za-z0-9_.$=+/-]+$'; then
  fail "CLERK_PUBLISHABLE_KEY has an invalid format"
fi

cat >"$output" <<EOF
window.__CLOUDX_CONFIG__ = Object.freeze({
  apiBaseUrl: "$api_base",
  clerkPublishableKey: "$clerk_key"
});
EOF

chmod 0444 "$output"
