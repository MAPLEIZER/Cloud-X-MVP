#!/usr/bin/env bash
set -euo pipefail
umask 027

MANAGER_IP="${1:-127.0.0.1}"
AGENT_NAME="${2:-linux-agent-$(hostname -s)}"
GROUP="${3:-default}"
WAZUH_AGENT_VERSION="${WAZUH_AGENT_VERSION:-}"

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

[[ -r /etc/os-release ]] || fail "/etc/os-release is unavailable."
# shellcheck disable=SC1091
. /etc/os-release
ID_LIKE="${ID_LIKE:-}"

install_debian() {
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq
    apt-get install -y -qq --no-install-recommends ca-certificates curl gnupg

    local key_tmp
    key_tmp="$(mktemp)"
    curl --fail --silent --show-error --location \
        https://packages.wazuh.com/key/GPG-KEY-WAZUH \
        --output "$key_tmp"
    gpg --batch --yes --dearmor --output /usr/share/keyrings/wazuh.gpg "$key_tmp"
    rm -f "$key_tmp"
    chmod 0644 /usr/share/keyrings/wazuh.gpg

    cat > /etc/apt/sources.list.d/wazuh.list <<'EOF'
deb [signed-by=/usr/share/keyrings/wazuh.gpg] https://packages.wazuh.com/4.x/apt/ stable main
EOF
    apt-get update -qq

    local package="wazuh-agent"
    if [[ -n "$WAZUH_AGENT_VERSION" ]]; then
        package="wazuh-agent=$WAZUH_AGENT_VERSION"
    fi

    WAZUH_MANAGER="$MANAGER_IP" \
    WAZUH_REGISTRATION_SERVER="$MANAGER_IP" \
    WAZUH_AGENT_NAME="$AGENT_NAME" \
    WAZUH_AGENT_GROUP="$GROUP" \
        apt-get install -y -qq "$package"
}

install_rhel() {
    local pkg_mgr="yum"
    command -v dnf >/dev/null 2>&1 && pkg_mgr="dnf"

    "$pkg_mgr" install -y ca-certificates curl
    rpm --import https://packages.wazuh.com/key/GPG-KEY-WAZUH

    cat > /etc/yum.repos.d/wazuh.repo <<'EOF'
[wazuh]
gpgcheck=1
gpgkey=https://packages.wazuh.com/key/GPG-KEY-WAZUH
enabled=1
name=Wazuh repository
baseurl=https://packages.wazuh.com/4.x/yum/
priority=1
EOF

    local package="wazuh-agent"
    if [[ -n "$WAZUH_AGENT_VERSION" ]]; then
        package="wazuh-agent-$WAZUH_AGENT_VERSION"
    fi

    WAZUH_MANAGER="$MANAGER_IP" \
    WAZUH_REGISTRATION_SERVER="$MANAGER_IP" \
    WAZUH_AGENT_NAME="$AGENT_NAME" \
    WAZUH_AGENT_GROUP="$GROUP" \
        "$pkg_mgr" install -y "$package"
}

case " $ID $ID_LIKE " in
    *" debian "*|*" ubuntu "*) install_debian ;;
    *" rhel "*|*" centos "*|*" fedora "*|*" rocky "*|*" almalinux "*) install_rhel ;;
    *) fail "Unsupported Linux distribution: ${ID:-unknown}" ;;
esac

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
POST_INSTALL="$SCRIPT_DIR/cloudx-agent-setup.sh"
if [[ -f "$POST_INSTALL" ]]; then
    chmod 0750 "$POST_INSTALL"
    "$POST_INSTALL"
else
    fail "Required post-install script is missing."
fi

systemctl daemon-reload
systemctl enable wazuh-agent >/dev/null
systemctl restart wazuh-agent
systemctl is-active --quiet wazuh-agent || fail "Wazuh agent failed to start."

log "Wazuh agent installed and running for manager $MANAGER_IP."
