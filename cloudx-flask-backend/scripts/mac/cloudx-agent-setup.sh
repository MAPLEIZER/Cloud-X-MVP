#!/usr/bin/env bash
set -euo pipefail
umask 027

WAZUH_PATH="/Library/Ossec"
ACTIVE_RESPONSE_BIN="$WAZUH_PATH/active-response/bin"
ETC_DIR="$WAZUH_PATH/etc"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
THREAT_SCRIPT="$SCRIPT_DIR/remove-threat.py"

log() { printf '[Cloud-X] %s\n' "$*"; }
fail() { printf '[Cloud-X] ERROR: %s\n' "$*" >&2; exit 1; }

if (( EUID != 0 )); then
    fail "Run this setup as root."
fi

command -v python3 >/dev/null 2>&1 \
    || fail "Python 3 must be pre-provisioned through an approved software-management process."
python3 -c 'import psutil' >/dev/null 2>&1 \
    || fail "Python psutil must be pre-provisioned through an approved software-management process."
[[ -f "$THREAT_SCRIPT" ]] || fail "remove-threat.py is missing from the deployment bundle."
[[ -d "$ACTIVE_RESPONSE_BIN" ]] || fail "Wazuh active-response directory does not exist."

OWNER_GROUP="admin"
if dscl . -read /Groups/wazuh >/dev/null 2>&1; then
    OWNER_GROUP="wazuh"
fi

install -o root -g "$OWNER_GROUP" -m 0750 \
    "$THREAT_SCRIPT" "$ACTIVE_RESPONSE_BIN/remove-threat.py"

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
chown root:"$OWNER_GROUP" "$CONF_FILE"
chmod 0640 "$CONF_FILE"

install -d -o root -g "$OWNER_GROUP" -m 0700 "$WAZUH_PATH/quarantine/cloudx"

if launchctl print system/com.wazuh.agent >/dev/null 2>&1; then
    launchctl kickstart -k system/com.wazuh.agent
fi

log "macOS active-response setup complete."
