#!/bin/bash
set -e

# =========================================================================================
# Cloud-X Security Agent Uninstaller (macOS)
# =========================================================================================
# Comprehensive uninstaller for Cloud-X Security Agent on macOS.
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
        log_error "Please run as root (sudo)."
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

# 1. Stop Services
log_info "Stopping Wazuh Agent..."
if [ -f /Library/Ossec/bin/wazuh-control ]; then
    /Library/Ossec/bin/wazuh-control stop >/dev/null 2>&1
    log_success "Service stopped."
else
    log_warn "Wazuh control binary not found, script might have been removed already."
fi

# 2. Remove LaunchDaemon
log_info "Removing LaunchDaemon..."
if [ -f /Library/LaunchDaemons/com.wazuh.agent.plist ]; then
    launchctl unload /Library/LaunchDaemons/com.wazuh.agent.plist >/dev/null 2>&1
    rm -f /Library/LaunchDaemons/com.wazuh.agent.plist
    log_success "LaunchDaemon removed."
fi

# 3. Remove Directories
log_info "Removing installation directory..."
if [ -d /Library/Ossec ]; then
    rm -rf /Library/Ossec
    log_success "Removed /Library/Ossec"
else
    log_info "/Library/Ossec not found"
fi

# 4. Remove Receipt
log_info "Removing installer receipt..."
pkgutil --forget com.wazuh.agent >/dev/null 2>&1 || true
log_success "Receipt removed."

# 5. Remove User
log_info "Removing wazuh user/group..."
dscl . -delete /Users/wazuh >/dev/null 2>&1 || true
dscl . -delete /Groups/wazuh >/dev/null 2>&1 || true
log_success "User/Group removed."

# 6. Summary
echo ""
echo -e "${GREEN}================================================================================${NC}"
echo -e "${GREEN}                         UNINSTALL COMPLETED SUCCESSFULLY                       ${NC}"
echo -e "${GREEN}================================================================================${NC}"
echo ""
log_success "System is clean."
