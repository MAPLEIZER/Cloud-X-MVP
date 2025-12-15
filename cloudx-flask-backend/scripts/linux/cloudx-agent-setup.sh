#!/bin/bash
set -e

# =========================================================================================
# Cloud-X Security Post-Installation Setup (Linux)
# =========================================================================================

# --- Configuration ---
WAZUH_PATH="/var/ossec"
ACTIVE_RESPONSE_BIN="$WAZUH_PATH/active-response/bin"
ETC_DIR="$WAZUH_PATH/etc"
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
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
        log_error "Please run as root."
        exit 1
    fi
}

check_root

log_info "Starting Post-Installation Setup..."

# 1. Install Dependencies
log_info "Installing Python dependencies..."
if command -v pip3 >/dev/null 2>&1; then
    pip3 install -r "$REQUIREMENTS" >/dev/null 2>&1
    log_info "Dependencies installed."
else
    log_warn "pip3 not found. Attempting to install 'psutil' using system package manager..."
    # Fallback to system package if pip is missing
    if [ -f /etc/debian_version ]; then
        apt-get update -qq && apt-get install python3-psutil -y -qq
    elif [ -f /etc/redhat-release ]; then
        yum install python3-psutil -y -q
    else
        log_error "Could not install dependencies. Please install 'python3-psutil' manually."
    fi
fi

# 2. Deploy Active Response Script
log_info "Deploying Active Response script..."
if [ -f "$THREAT_SCRIPT" ]; then
    cp "$THREAT_SCRIPT" "$ACTIVE_RESPONSE_BIN/remove-threat.py"
    chmod 750 "$ACTIVE_RESPONSE_BIN/remove-threat.py"
    chown root:wazuh "$ACTIVE_RESPONSE_BIN/remove-threat.py" 2>/dev/null || chown root:root "$ACTIVE_RESPONSE_BIN/remove-threat.py"
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
chown root:wazuh "$CONF_FILE" 2>/dev/null || chown root:root "$CONF_FILE"
log_info "Configuration created at $CONF_FILE"

# 4. Restart Service
log_info "Restarting Wazuh Agent..."
systemctl restart wazuh-agent
log_info "Post-installation setup complete."
