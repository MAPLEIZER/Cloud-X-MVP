#!/bin/bash
set -e

# =========================================================================================
# Cloud-X Security Agent Installer (macOS)
# =========================================================================================
# Professional installer for Cloud-X Security Agent on macOS.
# =========================================================================================

# --- Configuration ---
MANAGER_IP="${1:-127.0.0.1}"
AGENT_NAME="${2:-mac-agent-$(hostname)}"
GROUP="${3:-default}"
WAZUH_PKG_URL="https://packages.wazuh.com/4.x/macos/wazuh-agent-4.7.2-1.intel64.pkg" # Currently Intel/Universal
INSTALLER_PKG="/tmp/wazuh-agent.pkg"

# --- Colors & Formatting ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# --- Helper Functions ---

print_banner() {
    clear
    echo -e "${BLUE}                                                                                                    ${NC}"
    echo -e "${BLUE}                                                                                                    ${NC}"
    echo -e "${BLUE}                                               @@@@@                                                ${NC}"
    echo -e "${BLUE}                                            @@@      @@                                             ${NC}"
    echo -e "${BLUE}                                          @@             @@                                         ${NC}"
    echo -e "${BLUE}                                     @@@@@@         @@@@@@@@@@@                                     ${NC}"
    echo -e "${BLUE}                                    @@@           @@@         @@                                    ${NC}"
    echo -e "${BLUE}                                   @@           @@@  @@@@@@@@@ @@                                   ${NC}"
    echo -e "${BLUE}                                   @@ @       @@@  @@@       @ @@                                   ${NC}"
    echo -e "${BLUE}                                   @@ @@    @@@  @@@         @ @@                                   ${NC}"
    echo -e "${BLUE}                                    @@   @@    @@@            @@                                    ${NC}"
    echo -e "${BLUE}                                     @@@@@@@@@@@       @@@@@@@                                      ${NC}"
    echo -e "${BLUE}                                         @@@                                                        ${NC}"
    echo -e "${BLUE}                                                                                                    ${NC}"
    echo -e "${BLUE}                                    @@                     @@    @    @                             ${NC}"
    echo -e "${BLUE}                               @    @@   @@             @  @     @@  @                              ${NC}"
    echo -e "${BLUE}                             @@@@@@ @@ @@@@@@  @@  @@ @@@@@@       @@                               ${NC}"
    echo -e "${BLUE}                            @@      @@ @@   @@ @   @@ @    @      @ @@                              ${NC}"
    echo -e "${BLUE}                             @@@@@@ @@ @@@@@@  @@@@@@ @@@@@@@    @   @@                             ${NC}"
    echo -e "${BLUE}                                                                                                    ${NC}"
    echo -e "${BLUE}                                                                                                    ${NC}"
    echo -e "${BLUE}                                                                                                    ${NC}"
    echo ""
    echo -e "\033[42;37m                       CLOUD-X SECURITY WAZUH AGENT ENTERPRISE SETUP                         ${NC}"
    echo -e "\033[42;37m                              Version 3.1 - Enhanced Security                           ${NC}"
    echo -e "\033[42;33m                                   $(date -u '+%Y-%m-%d %H:%M:%S UTC')                              ${NC}"
    echo -e "\033[42;36m                                     by CLOUD-X SECURITY                                  ${NC}"
    echo ""
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run as root (sudo)."
        exit 1
    fi
}

cleanup() {
    if [ $? -ne 0 ]; then
        echo ""
        log_error "SETUP FAILED. See logs for details."
        echo -e "${YELLOW}Troubleshooting:${NC}"
        echo "1. Check internet connectivity."
        echo "2. Ensure you have root privileges."
    fi
    # Remove installer
    rm -f "$INSTALLER_PKG"
}
trap cleanup EXIT

# --- Main Installation Logic ---

print_banner
check_root

log_info "Starting installation..."
log_info "Target Manager: ${BOLD}$MANAGER_IP${NC}"
log_info "Agent Name:     ${BOLD}$AGENT_NAME${NC}"
echo ""

# 1. Download
log_info "Downloading Wazuh Agent Package..."
curl -L -s -o "$INSTALLER_PKG" "$WAZUH_PKG_URL"

if [ ! -f "$INSTALLER_PKG" ]; then
    log_error "Failed to download installer."
    exit 1
fi

# 2. Install
log_info "Running Installer (this may take a moment)..."
installer -pkg "$INSTALLER_PKG" -target / >/dev/null

# 3. Configure
log_info "Configuring Agent..."
# Register with manager
/Library/Ossec/bin/agent-auth -m "$MANAGER_IP" -A "$AGENT_NAME" || log_warn "Auto-registration failed (legacy or connectivity issue). Check manager logs."

# Update Config
log_info "Updating ossec.conf..."
sed -i '' "s/MANAGER_IP/$MANAGER_IP/g" /Library/Ossec/etc/ossec.conf

# 4. Post-Install Setup
log_info "Running Post-Installation Setup..."
SCRIPT_DIR="$(dirname "$0")"
POST_INSTALL="$SCRIPT_DIR/cloudx-agent-setup.sh"

if [ -f "$POST_INSTALL" ]; then
    chmod +x "$POST_INSTALL"
    "$POST_INSTALL"
else
    log_warn "post-install-setup.sh not found in $SCRIPT_DIR. Skipping additional configuration."
fi

# 5. Start
log_info "Starting Service..."
/Library/Ossec/bin/wazuh-control start >/dev/null

# 6. Verification
if /Library/Ossec/bin/wazuh-control status | grep -q "running"; then
    echo ""
    echo -e "${GREEN}   ================================================${NC}"
    echo -e "${GREEN}             SETUP SUCCESSFUL                      ${NC}"
    echo -e "${GREEN}   ================================================${NC}"
    echo ""
    log_info "Agent is running."
else
    log_error "Service failed to start."
    exit 1
fi
