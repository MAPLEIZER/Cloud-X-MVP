#!/bin/bash
set -e

# =========================================================================================
# Cloud-X Security Agent Installer (Linux)
# =========================================================================================
# Professional installer for Cloud-X Security Agent on Linux systems.
# Features:
# - Auto-detection of Debian/RHEL based systems
# - Secure repository configuration
# - Automatic agent configuration and registration
# - Robust error handling and color-coded logging
# =========================================================================================

# --- Configuration ---
MANAGER_IP="${1:-127.0.0.1}"
AGENT_NAME="${2:-linux-agent-$(hostname)}"
GROUP="${3:-default}"
WAZUH_VERSION="4.7.2-1"

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
        log_error "Please run as root or with sudo."
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
        echo "3. Verify the Manager IP ($MANAGER_IP) is reachable."
    fi
}
trap cleanup EXIT

# --- Main Installation Logic ---

print_banner
check_root

log_info "Starting installation..."
log_info "Target Manager: ${BOLD}$MANAGER_IP${NC}"
log_info "Agent Name:     ${BOLD}$AGENT_NAME${NC}"
log_info "Group:          ${BOLD}$GROUP${NC}"
echo ""

# 1. Detect OS & Install Dependencies
log_info "Detecting Operating System..."

if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$NAME
    VER=$VERSION_ID
    log_info "OS Detected: $OS $VER"
else
    log_error "Cannot detect OS. /etc/os-release not found."
    exit 1
fi

if [[ "$ID" == "debian" || "$ID_LIKE" == "debian" || "$ID" == "ubuntu" ]]; then
    PKG_MGR="apt-get"
    log_info "Using apt-get package manager."
    
    log_info "Installing prerequisites (curl, gnupg, lsb-release)..."
    $PKG_MGR update -y -qq >/dev/null
    $PKG_MGR install curl gnupg lsb-release -y -qq >/dev/null
    
    log_info "Adding Wazuh repository..."
    curl -s https://packages.wazuh.com/key/GPG-KEY-WAZUH | apt-key add - 2>/dev/null
    echo "deb https://packages.wazuh.com/4.x/apt/ stable main" | tee /etc/apt/sources.list.d/wazuh.list >/dev/null
    $PKG_MGR update -y -qq >/dev/null

    log_info "Installing Wazuh Agent..."
    WAZUH_MANAGER="$MANAGER_IP" WAZUH_AGENT_NAME="$AGENT_NAME" WAZUH_AGENT_GROUP="$GROUP" $PKG_MGR install wazuh-agent -y -qq >/dev/null

elif [[ "$ID" == "rhel" || "$ID_LIKE" == "rhel" || "$ID" == "centos" || "$ID" == "fedora" ]]; then
    PKG_MGR="yum"
    log_info "Using yum/dnf package manager."
    
    log_info "Importing GPG key..."
    rpm --import https://packages.wazuh.com/key/GPG-KEY-WAZUH
    
    log_info "Adding Wazuh repository..."
    cat > /etc/yum.repos.d/wazuh.repo << EOF
[wazuh]
gpgcheck=1
gpgkey=https://packages.wazuh.com/key/GPG-KEY-WAZUH
enabled=1
name=EL-\$releasever - Wazuh
baseurl=https://packages.wazuh.com/4.x/yum/
protect=1
EOF

    log_info "Installing Wazuh Agent..."
    WAZUH_MANAGER="$MANAGER_IP" WAZUH_AGENT_NAME="$AGENT_NAME" WAZUH_AGENT_GROUP="$GROUP" $PKG_MGR install wazuh-agent -y -q >/dev/null
else
    log_error "Unsupported Operating System: $ID"
    exit 1
fi

# 2. Configure Agent
log_info "Configuring Agent..."
# Just in case the env vars didn't take or we need to enforce:
sed -i "s/^<client>/<client><server><address>$MANAGER_IP<\/address><\/server>/" /var/ossec/etc/ossec.conf
# Note: More robust XML parsing would be better, but sed is standard for simple replacement if structure implies

# 3. Enable & Start
log_info "Enabling and Starting Service..."
systemctl daemon-reload
systemctl enable wazuh-agent >/dev/null 2>&1
systemctl restart wazuh-agent

# 4. Verification
if systemctl is-active --quiet wazuh-agent; then
    echo ""
    echo -e "${GREEN}   ================================================${NC}"
    echo -e "${GREEN}             SETUP SUCCESSFUL                      ${NC}"
    echo -e "${GREEN}   ================================================${NC}"
    echo ""
    log_info "Agent is running."
    log_info "Logs available at: /var/ossec/logs/ossec.log"
else
    log_error "Service failed to start. Check logs."
    exit 1
fi
