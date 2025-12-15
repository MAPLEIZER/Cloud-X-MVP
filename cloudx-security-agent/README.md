

<p align="center">
  <img src="./documentation/cloud-x logo.png" alt="Cloud-X Security Logo" width="200"/>
</p>

# Cloud-X Security Wazuh Agent Installer

Enterprise-grade standalone Wazuh agent installer and uninstaller with enhanced MSI service management, smart IP configuration, and robust error handling.

[![PowerShell](https://img.shields.io/badge/PowerShell-5.1%2B-blue.svg)](https://github.com/PowerShell/PowerShell)
[![Windows](https://img.shields.io/badge/Windows-10%2B-green.svg)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-3.1--GitHub-orange.svg)](CHANGELOG.md)

## 📋 Table of Contents

- [Features](#-features)
- [Prerequisites](#-prerequisites)
- [How to Run](#-how-to-run)
- [Configuration](#-configuration)
- [Uninstaller](#-uninstaller)
- [Troubleshooting](#-troubleshooting)
- [Repository Structure](#-repository-structure)

## 🚀 Features

### 🔒 **Secure by Design**
- **SHA256 Hash Verification** - Verifies the integrity of the downloaded Wazuh agent installer.
- **HTTPS Enforcement** - Ensures secure communications by using TLS 1.2 for all downloads.
- **Administrator Enforcement** - Scripts require elevated privileges to run, ensuring system-level changes are authorized.
- **Audit Trail Generation** - Complete PowerShell transcript logging captures all actions for security and troubleshooting.

### ⚙️ **Standalone Architecture**
- **Self-Contained Modules** - Standalone PowerShell modules with all dependencies included
- **Enhanced MSI Management** - Automatic Windows Installer service restart when busy or hanging
- **Smart IP Configuration** - Personal group agents automatically use internal network IP (192.168.100.37)
- **Parameter-driven** - All key settings can be passed as command-line arguments
- **Robust Error Recovery** - Comprehensive retry logic with detailed MSI log analysis

### 📈 **Robust Functionality**
- **Pre-flight Checks** - Verifies system compatibility (e.g., disk space) before starting.
- **Automated Cleanup** - Removes downloaded setup files after a successful installation.
- **Color-Coded Logging** - Provides clear, real-time feedback on the script's progress.
- **Comprehensive Uninstaller** - A dedicated, modular script for removing all traces of the Wazuh agent.

### 🛡️ **Automated Endpoint Hardening & Visibility**
- **Sysmon Integration**: Automatically installs and configures Sysmon with the SwiftOnSecurity configuration for deep system visibility.
- **Advanced Auditing**: Enables critical Windows audit policies for detailed tracking of process creation, object access, and logon events.
- **PowerShell Logging**: Activates script block and module logging to detect malicious in-memory attacks.
- **Security Configuration Assessment (SCA)**: The agent is pre-configured to run SCA scans, checking for compliance against CIS benchmarks.
- **Osquery Integration**: Seamlessly integrates osquery for rich host telemetry and advanced threat hunting.

### 📦 **Advanced Agent Configuration**
- The default `windows-agents/agent.conf` includes enhanced File Integrity Monitoring (FIM) with `whodata`, noise-reducing ignores, hardened active response timeouts, and an offline agent buffer.

## 🔧 Prerequisites

- **Operating System**: Windows 10 or Windows Server 2016+
- **PowerShell Version**: PowerShell 5.1 or higher
- **Permissions**: You must run scripts from an **elevated (Administrator)** PowerShell session.
- **Network**: Internet connectivity to download the Wazuh agent installer and connectivity to the Wazuh Manager IP.
- **Disk Space**: Minimum 500MB of free disk space.

## ⚡ Quick Start

Run the following command in an **elevated (Administrator)** PowerShell session to download and use the standalone installer module:

```powershell
# Download and import the standalone installer module
$params = @{
    ipAddress  = '192.168.1.100'
    agentName  = 'WIN-AGENT-01'
    groupLabel = 'windows_servers'
}

# Method 1: Direct standalone module download and import
$moduleUrl = "https://raw.githubusercontent.com/MAPLEIZER/Cloud-X-security-agent/main/wazuh-configs/scripts/windows/cloudx-agent-installer.psm1"
$moduleContent = (Invoke-WebRequest -Uri $moduleUrl -UseBasicParsing).Content
$moduleContent | Out-File -FilePath "$env:TEMP\cloudx-agent-installer.psm1" -Encoding UTF8
Import-Module "$env:TEMP\cloudx-agent-installer.psm1" -Force
Install-WazuhAgent @params

# Step 2: Run the Post-Install Hardening Script
# This script enables advanced features like Sysmon, enhanced auditing, and PowerShell logging.
# Note: If you cloned the repo, adjust the path accordingly.
$postInstallUrl = "https://raw.githubusercontent.com/MAPLEIZER/Cloud-X-security-agent/main/wazuh-configs/scripts/windows/cloudx-agent-setup.ps1"
$postInstallContent = (Invoke-WebRequest -Uri $postInstallUrl -UseBasicParsing).Content
$postInstallPath = "$env:TEMP\cloudx-agent-setup.ps1"
$postInstallContent | Out-File -FilePath $postInstallPath -Encoding UTF8
& $postInstallPath
```

### Alternative Installation Methods

```powershell
# Method 2: Clone repository and import locally
git clone https://github.com/MAPLEIZER/Cloud-X-security-agent.git
Import-Module ".\Cloud-X-security-agent\wazuh-configs\scripts\windows\cloudx-agent-installer.psm1" -Force
Install-WazuhAgent @params
```

## ⚙️ Configuration

This repository is designed to be a centralized location for managing your Wazuh agent configurations.

### **Agent Configuration (`/agents`)**

The `agents` directory contains templates for `ossec.conf`. You can define default configurations and create specific overrides for different operating systems or server roles.

- `agents/ossec.conf`: Default configuration for all agents.
- `agents/windows-agents/ossec.conf`: Specific overrides for Windows agents.
- `agents/linux-agents/ossec.conf`: Specific overrides for Linux agents.
- `agents/custom-groups/`: Define configurations for specific Wazuh groups (e.g., web servers, database servers).

### **Installer Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ipAddress` | String | Yes* | IP address of your Wazuh manager. |
| `agentName` | String | Yes* | A unique name for the new agent. |
| `groupLabel` | String | Yes* | The Wazuh group to assign the agent to. |
| `ConfigFile` | String | Yes* | Path to your JSON configuration file. |
| `Uninstall` | Switch | Yes* | Runs the uninstaller instead of the installer. |
| `WAZUH_VERSION` | String | No | The Wazuh agent version to install. Defaults to `4.7.0-1`. |
| `LogPath` | String | No | Custom file path for the transcript log. |
| `SKIP_HASH_CHECK` | Switch | No | Skips SHA256 hash verification. **Not recommended.** |
| `KeepLogs` | Switch | No | Used with `-Uninstall` to preserve log directories. |

*Either `ipAddress`/`agentName`/`groupLabel`, `ConfigFile`, or `Uninstall` parameter set must be used.

## 🛡️ Uninstaller

A powerful, standalone uninstaller module is included to completely and safely remove all traces of the Wazuh agent.

### **How to Run the Uninstaller**

Download and run the standalone uninstaller module:

```powershell
# Download and import the standalone uninstaller module
$uninstallerUrl = "https://raw.githubusercontent.com/MAPLEIZER/Cloud-X-security-agent/main/wazuh-configs/scripts/windows/cloudx-agent-uninstaller.psm1"
$uninstallerContent = (Invoke-WebRequest -Uri $uninstallerUrl -UseBasicParsing).Content
$uninstallerContent | Out-File -FilePath "$env:TEMP\cloudx-agent-uninstaller.psm1" -Encoding UTF8
Import-Module "$env:TEMP\cloudx-agent-uninstaller.psm1" -Force
Remove-WazuhAgent
```

### **Uninstaller Parameters**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `-Force` | Switch | No | Bypasses the confirmation prompt. |
| `-KeepLogs` | Switch | No | Preserves Wazuh log directories during cleanup. |

## 🚨 Troubleshooting

If the script fails, a `SETUP FAILED` message will appear.

1.  **Check Administrator Privileges**: The most common issue is not running PowerShell as an Administrator.
2.  **Check Network Connectivity**: Ensure the machine can reach the internet and that the Wazuh manager IP is correct and reachable.
3.  **Review the Log File**: The script will output the path to a transcript log (e.g., `Cloud-X-Security-Wazuh-Installer-*.log`). This file contains a complete record of the execution and will have detailed error messages.
4.  **Verify Parameters**: Double-check that all parameters are correct. If using a config file, ensure the path is correct and the JSON is valid.

## 📁 Repository Structure

```
NixGuard-Wazuh-Installer/
├── documentation/
│   ├── Agent-Server-Integration.md
│   └── Post-Install.md
├── wazuh-configs/
│   ├── agents/
│   │   ├── custom-groups/
│   │   ├── linux-agents/
│   │   ├── mac-agents/
│   │   └── windows-agents/
│   └── scripts/
│       ├── custom-groups/
│       ├── linux/
│       ├── mac/
│       └── windows/
│           └── ... (Windows-specific scripts)
└── README.md
```

## 🏗️ Standalone Module Architecture

The installer and uninstaller use self-contained standalone modules for simplified deployment:

### **Standalone Installer Module** (`windows/CloudXSecurityInstaller-Standalone.psm1`)
- **All-in-One Design**: Contains all dependencies inline - no external module requirements
- **Enhanced MSI Management**: Automatic service restart when Windows Installer is busy
- **Smart IP Configuration**: Personal group uses internal IP (192.168.100.37)
- **Professional UI**: ASCII art banner and color-coded logging
- **Comprehensive Error Handling**: Detailed MSI log analysis and retry logic

### **Standalone Uninstaller Module** (`windows/CloudXSecurityUninstaller-Standalone.psm1`)
- **Complete Removal**: Stops services, removes MSI, cleans registry and files
- **Safety Features**: Confirmation prompts with Force override option
- **Detailed Logging**: Color-coded progress tracking and summary display
- **Self-Contained**: No external dependencies required

---

<p align="center">
  <strong>Made with ❤️ by MAPLEIZER</strong>
</p>
