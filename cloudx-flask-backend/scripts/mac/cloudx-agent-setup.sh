#!/bin/bash
set -e

# =========================================================================================
# Cloud-X Security Post-Installation Setup (macOS)
# =========================================================================================

# --- Configuration ---
WAZUH_PATH="/Library/Ossec"
ACTIVE_RESPONSE_BIN="$WAZUH_PATH/active-response/bin"
ETC_DIR="$WAZUH_PATH/etc"
SCRIPT_DIR="$(dirname "$0")"
THREAT_SCRIPT="$SCRIPT_DIR/remove-threat.py"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"

# --- Colors ---
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run as root (sudo)."
        exit 1
    fi
}

check_root

log_info "Starting Post-Installation Setup..."

# 1. Install Dependencies
log_info "Installing Python dependencies..."
# Check for pip3
if command -v pip3 >/dev/null 2>&1; then
    pip3 install -r "$REQUIREMENTS" --break-system-packages >/dev/null 2>&1 || pip3 install -r "$REQUIREMENTS" >/dev/null 2>&1
    log_info "Dependencies installed."
else
    log_warn "pip3 not found. Please ensure python3 and pip3 are installed."
    # Attempt to use python3 -m pip
    if command -v python3 >/dev/null 2>&1; then
         python3 -m pip install -r "$REQUIREMENTS" --break-system-packages >/dev/null 2>&1 || python3 -m pip install -r "$REQUIREMENTS" >/dev/null 2>&1
         log_info "Dependencies installed via python3 module."
    fi
fi

# 2. Deploy Active Response Script
log_info "Deploying Active Response script..."
if [ -f "$THREAT_SCRIPT" ]; then
    cp "$THREAT_SCRIPT" "$ACTIVE_RESPONSE_BIN/remove-threat.py"
    chmod 750 "$ACTIVE_RESPONSE_BIN/remove-threat.py"
    chown root:wazuh "$ACTIVE_RESPONSE_BIN/remove-threat.py" 2>/dev/null || chown root:admin "$ACTIVE_RESPONSE_BIN/remove-threat.py"
    log_info "Script deployed to $ACTIVE_RESPONSE_BIN/remove-threat.py"
else
    log_error "remove-threat.py not found in $SCRIPT_DIR"
fi

# 3. Configure Active Response
log_info "Configuring Active Response..."
CONF_FILE="$ETC_DIR/cloudx_active_response.conf"

cat > "$CONF_FILE" << EOF
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

chmod 640 "$CONF_FILE"
chown root:wazuh "$CONF_FILE" 2>/dev/null || chown root:admin "$CONF_FILE"
log_info "Configuration created at $CONF_FILE"

# 4. Restart Service
log_info "Restarting Wazuh Agent..."
/Library/Ossec/bin/wazuh-control restart
log_info "Post-installation setup complete."
