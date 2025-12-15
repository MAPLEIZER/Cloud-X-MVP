#!/bin/bash
set -e

# =========================================================================================
# Cloud-X Security Agent Uninstaller (Linux)
# =========================================================================================
# Comprehensive uninstaller for Cloud-X Security Agent on Linux systems.
# =========================================================================================

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
    echo -e "${RED}                                                                                                    ${NC}"
    echo -e "${RED}                                                                                                    ${NC}"
    echo -e "${RED}                                               @@@@@                                                ${NC}"
    echo -e "${RED}                                            @@@      @@                                             ${NC}"
    echo -e "${RED}                                          @@             @@                                         ${NC}"
    echo -e "${RED}                                     @@@@@@         @@@@@@@@@@@                                     ${NC}"
    echo -e "${RED}                                    @@@           @@@         @@                                    ${NC}"
    echo -e "${RED}                                   @@           @@@  @@@@@@@@@ @@                                   ${NC}"
    echo -e "${RED}                                   @@ @       @@@  @@@       @ @@                                   ${NC}"
    echo -e "${RED}                                   @@ @@    @@@  @@@         @ @@                                   ${NC}"
    echo -e "${RED}                                    @@   @@    @@@            @@                                    ${NC}"
    echo -e "${RED}                                     @@@@@@@@@@@       @@@@@@@                                      ${NC}"
    echo -e "${RED}                                         @@@                                                        ${NC}"
    echo -e "${RED}                                                                                                    ${NC}"
    echo -e "${RED}                                    @@                     @@    @    @                             ${NC}"
    echo -e "${RED}                               @    @@   @@             @  @     @@  @                              ${NC}"
    echo -e "${RED}                             @@@@@@ @@ @@@@@@  @@  @@ @@@@@@       @@                               ${NC}"
    echo -e "${RED}                            @@      @@ @@   @@ @   @@ @    @      @ @@                              ${NC}"
    echo -e "${RED}                             @@@@@  @@ @@@@@@  @@@@@@ @@@@@@@    @   @@                             ${NC}"
    echo -e "${RED}                                                                                                    ${NC}"
    echo -e "${RED}                                                                                                    ${NC}"
    echo -e "${RED}                                                                                                    ${NC}"
    echo ""
    echo -e "\033[41;37m                       CLOUD-X SECURITY WAZUH AGENT COMPLETE UNINSTALLER                    ${NC}"
    echo -e "\033[41;37m                              Version 1.1 - Complete Removal                           ${NC}"
    echo -e "\033[41;33m                                   $(date -u '+%Y-%m-%d %H:%M:%S UTC')                              ${NC}"
    echo -e "\033[41;36m                                     by CLOUD-X SECURITY                                  ${NC}"
    echo ""
}

log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Please run as root or with sudo."
        exit 1
    fi
}

# --- Main Uninstall Logic ---

print_banner
check_root

log_info "Cloud-X Security Agent Uninstaller started..."
echo ""
echo -e "${YELLOW}This will completely remove Cloud-X Security Agent and Wazuh from your system.${NC}"
read -p "Are you sure you want to continue? (y/N): " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
    log_warn "Uninstallation cancelled by user."
    exit 0
fi
echo ""

# 1. Detect OS
log_info "Detecting Operating System..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
else
    log_error "Cannot detect OS. /etc/os-release not found."
    exit 1
fi

# 2. Stop Services
log_info "Stopping Wazuh Agent service..."
if command -v systemctl >/dev/null 2>&1; then
    systemctl stop wazuh-agent >/dev/null 2>&1 || true
    systemctl disable wazuh-agent >/dev/null 2>&1 || true
    log_success "Service stopped."
elif command -v service >/dev/null 2>&1; then
    service wazuh-agent stop >/dev/null 2>&1 || true
    log_success "Service stopped."
else
    log_warn "Could not stop service (systemctl/service not found)."
fi

# 3. Remove Package
log_info "Removing Wazuh Agent package..."
if [[ "$ID" == "debian" || "$ID_LIKE" == "debian" || "$ID" == "ubuntu" ]]; then
    apt-get remove --purge wazuh-agent -y >/dev/null 2>&1
    apt-get autoremove -y >/dev/null 2>&1
elif [[ "$ID" == "rhel" || "$ID_LIKE" == "rhel" || "$ID" == "centos" || "$ID" == "fedora" ]]; then
    yum remove wazuh-agent -y >/dev/null 2>&1
else
    log_warn "Unsupported package manager. Skipping package removal."
fi
log_success "Package removed."

# 4. Remove Directories
log_info "Cleaning up directories..."
DIRS_TO_REMOVE=(
    "/var/ossec"
    "/etc/ossec-init.conf"
    "/etc/apt/sources.list.d/wazuh.list"
    "/etc/yum.repos.d/wazuh.repo"
)

for DIR in "${DIRS_TO_REMOVE[@]}"; do
    if [ -e "$DIR" ]; then
        rm -rf "$DIR"
        log_success "Removed $DIR"
    fi
done

# 5. Summary
echo ""
echo -e "${GREEN}================================================================================${NC}"
echo -e "${GREEN}                         UNINSTALL COMPLETED SUCCESSFULLY                       ${NC}"
echo -e "${GREEN}================================================================================${NC}"
echo ""
log_success "System is clean."
