#!/usr/bin/env bash
set -euo pipefail
umask 027

WAZUH_PATH="/var/ossec"
ACTIVE_RESPONSE_BIN="$WAZUH_PATH/active-response/bin"
ETC_DIR="$WAZUH_PATH/etc"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
THREAT_SCRIPT="$SCRIPT_DIR/remove-threat.py"

log() { printf '[Cloud-X] %s\n' "$*"; }
fail() { printf '[Cloud-X] ERROR: %s\n' "$*" >&2; exit 1; }

if (( EUID != 0 )); then
    fail "Run this setup as root."
fi

if ! python3 -c 'import psutil' >/dev/null 2>&1; then
    log "Installing psutil from the operating-system package repository."
    if command -v apt-get >/dev/null 2>&1; then
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -qq
        apt-get install -y -qq --no-install-recommends python3-psutil
    elif command -v dnf >/dev/null 2>&1; then
        dnf install -y python3-psutil
    elif command -v yum >/dev/null 2>&1; then
        yum install -y python3-psutil
    else
        fail "No supported package manager was found for python3-psutil."
    fi
fi

python3 -c 'import psutil' >/dev/null 2>&1 || fail "psutil is unavailable after installation."
[[ -f "$THREAT_SCRIPT" ]] || fail "remove-threat.py is missing from the installer bundle."
[[ -d "$ACTIVE_RESPONSE_BIN" ]] || fail "Wazuh active-response directory does not exist."

install -o root -g root -m 0750 "$THREAT_SCRIPT" "$ACTIVE_RESPONSE_BIN/remove-threat.py"
if getent group wazuh >/dev/null 2>&1; then
    chgrp wazuh "$ACTIVE_RESPONSE_BIN/remove-threat.py"
fi

CONF_FILE="$ETC_DIR/cloudx_active_response.conf"
cat > "$CONF_FILE" <<'EOF'
<!-- Cloud-X Security Active Response Configuration -->
<command>
  <name>remove-threat</name>
  <executable>remove-threat.py</executable>
  <timeout_allowed>yes</timeout_allowed>
</command>

<active-response>
  <command>remove-threat</command>
  <location>local</location>
  <rules_id>100543,100546,100547</rules_id>
  <timeout>60</timeout>
</active-response>
EOF
chmod 0640 "$CONF_FILE"
if getent group wazuh >/dev/null 2>&1; then
    chown root:wazuh "$CONF_FILE"
else
    chown root:root "$CONF_FILE"
fi

install -d -o root -g root -m 0700 /var/ossec/quarantine/cloudx
systemctl restart wazuh-agent
systemctl is-active --quiet wazuh-agent || fail "Wazuh agent failed after active-response setup."

log "Active-response setup complete."
