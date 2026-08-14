#!/usr/bin/env bash
set -euo pipefail
umask 077

MANAGER_IP="${1:-127.0.0.1}"
AGENT_NAME="${2:-mac-agent-$(hostname -s)}"
GROUP="${3:-default}"
WAZUH_AGENT_VERSION="${WAZUH_AGENT_VERSION:-4.14.7-1}"

log() { printf '[Cloud-X] %s\n' "$*"; }
fail() { printf '[Cloud-X] ERROR: %s\n' "$*" >&2; exit 1; }

if (( EUID != 0 )); then
    fail "Run this installer as root."
fi
if [[ ! "$MANAGER_IP" =~ ^[A-Za-z0-9:][A-Za-z0-9.:-]{0,252}$ ]]; then
    fail "Invalid Wazuh manager address."
fi
if [[ ! "$AGENT_NAME" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$ ]]; then
    fail "Invalid agent name."
fi
if [[ ! "$GROUP" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$ ]]; then
    fail "Invalid agent group."
fi
if [[ ! "$WAZUH_AGENT_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+-[0-9]+$ ]]; then
    fail "Invalid Wazuh version format."
fi

case "$(uname -m)" in
    arm64) WAZUH_ARCH="arm64" ;;
    x86_64) WAZUH_ARCH="intel64" ;;
    *) fail "Unsupported macOS architecture: $(uname -m)" ;;
esac

PKG_FILE="$(mktemp "/tmp/cloudx-wazuh-${WAZUH_AGENT_VERSION}.XXXXXX.pkg")"
ENV_FILE="$(mktemp /tmp/cloudx-wazuh-env.XXXXXX)"
cleanup() {
    rm -f -- "$PKG_FILE" "$ENV_FILE" /tmp/wazuh_envs
}
trap cleanup EXIT INT TERM

PKG_URL="https://packages.wazuh.com/4.x/macos/wazuh-agent-${WAZUH_AGENT_VERSION}.${WAZUH_ARCH}.pkg"
log "Downloading Wazuh agent ${WAZUH_AGENT_VERSION} for ${WAZUH_ARCH}."
curl --fail --silent --show-error --location --proto '=https' --tlsv1.2 \
    --output "$PKG_FILE" "$PKG_URL"

log "Verifying macOS package signature."
pkgutil --check-signature "$PKG_FILE" >/dev/null 2>&1 \
    || fail "The downloaded Wazuh package did not pass macOS signature verification."

cat > "$ENV_FILE" <<EOF
WAZUH_MANAGER='$MANAGER_IP'
WAZUH_REGISTRATION_SERVER='$MANAGER_IP'
WAZUH_AGENT_NAME='$AGENT_NAME'
WAZUH_AGENT_GROUP='$GROUP'
EOF
chmod 0600 "$ENV_FILE"
mv -f -- "$ENV_FILE" /tmp/wazuh_envs
chmod 0600 /tmp/wazuh_envs

log "Installing and enrolling Wazuh agent."
installer -pkg "$PKG_FILE" -target /
rm -f /tmp/wazuh_envs

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
POST_INSTALL="$SCRIPT_DIR/cloudx-agent-setup.sh"
[[ -f "$POST_INSTALL" ]] || fail "Required post-install script is missing."
chmod 0750 "$POST_INSTALL"
"$POST_INSTALL"

if launchctl print system/com.wazuh.agent >/dev/null 2>&1; then
    launchctl kickstart -k system/com.wazuh.agent
else
    launchctl bootstrap system /Library/LaunchDaemons/com.wazuh.agent.plist
fi

launchctl print system/com.wazuh.agent >/dev/null 2>&1 \
    || fail "Wazuh launch daemon is not loaded after installation."

log "Wazuh agent installed and running for manager $MANAGER_IP."
