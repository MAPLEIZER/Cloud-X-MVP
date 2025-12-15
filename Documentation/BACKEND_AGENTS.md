# Cloud-X Backend & Agent Documentation

This document details the architecture and usage of the Cloud-X Backend's deployment module (`deployer.py`), system monitoring features, and the associated agent scripts.

## 1. Agent Deployment Module (`deployer.py`)

The `AgentDeployer` class handles the remote installation of Cloud-X agents on target machines. It supports Windows, Linux, and macOS targets using protocol-specific methods (WinRM for Windows, SSH for Unix-like systems).

### Core Functionality

-   **Wrapper Class**: `AgentDeployer(scripts_dir)`
    -   Initializes with the base directory containing platform-specific agent scripts.

### Methods

#### `deploy_windows(target, username, password, manager_ip, agent_name, group)`
-   **Protocol**: WinRM (via `pywinrm`)
-   **Script Used**: `scripts/windows/cloudx-agent-installer.psm1`
-   **Process**:
    1.  Reads the PowerShell module content and the embedded Base64 certificate.
    2.  Constructs a remote PowerShell script block that:
        -   Installs the embedded certificate to the `Cert:\LocalMachine\Root` store.
        -   Writes the module to a temporary file on the target.
        -   Imports the module.
        -   Executes `Install-CloudXAgent` with the provided parameters.
    3.  Executes the script via WinRM.

#### `deploy_linux(target, username, password, manager_ip, agent_name, group)`
-   **Protocol**: SSH (via `paramiko`)
-   **Script Used**: `scripts/linux/cloudx-agent-install.sh`
-   **Additional Files Transferred**:
    -   `scripts/linux/cloudx-agent-setup.sh`
    -   `scripts/linux/remove-threat.py`
    -   `scripts/linux/requirements.txt`
-   **Process**:
    1.  Establishes an SSH connection.
    2.  Creates a temporary directory (`/tmp/cloudx_deploy_<timestamp>`).
    3.  Uploads the install script, setup script, and helper Python scripts (threat removal tools).
    4.  Makes scripts executable (`chmod +x`).
    5.  Runs the `cloudx-agent-install.sh` script with `sudo`, passing manager IP, agent name, and group as arguments.
    6.  The result includes the output of the installation script.

#### `deploy_mac(target, username, password, manager_ip, agent_name, group)`
-   **Protocol**: SSH (via `paramiko`)
-   **Script Used**: `scripts/mac/cloudx-agent-install.sh`
-   **Additional Files Transferred**:
    -   `scripts/mac/cloudx-agent-setup.sh`
    -   `scripts/linux/remove-threat.py` (Shared)
    -   `scripts/linux/requirements.txt` (Shared)
-   **Process**: Identical to Linux deployment, utilizing the Mac-specific install script but sharing the Python threat removal tools from the Linux directory.

---

## 2. Agent Scripts

The backend includes a set of scripts for each platform to handle the local installation, configuration, and uninstallation of the Cloud-X (Wazuh) agent.

### Naming Convention
All scripts follow the `cloudx-agent-[action].[ext]` convention.

### Windows (`scripts/windows/`)

| File | Description |
|------|-------------|
| `cloudx-agent-installer.psm1` | Primary PowerShell module for installing the agent. Configures manager IP, enrollment, and service startup. |
| `cloudx-agent-uninstaller.psm1` | Removes the agent, cleans up configuration files, and deregisters the service. |
| `cloudx-agent-setup.ps1` | Post-installation setup script for Sysmon, advanced auditing, and PowerShell logging. |
| `cloudx-code-signing.cer` | Code signing certificate for script verification. |
| `cloudx-powershell-rules.xml` | Custom Wazuh rules for monitoring PowerShell activity (e.g., detecting malicious commands). |
| `remove-threat.py` | Python script for automated threat removal and remediation. |
| `requirements.txt` | Python dependencies for `remove-threat.py`. |

### Linux (`scripts/linux/`)

| File | Description |
|------|-------------|
| `cloudx-agent-install.sh` | Bash script to install the Wazuh agent package (deb/rpm), configure `ossec.conf`, and start the service. |
| `install.sh` | Alternative installation script (legacy). |
| `cloudx-agent-uninstall.sh` | Removes the agent package and cleans up directories. |
| `cloudx-agent-setup.sh` | Post-install configuration and hardening checks. |
| `remove-threat.py` | Python script for automated threat removal and remediation. |
| `requirements.txt` | Python dependencies for `remove-threat.py`. |

### macOS (`scripts/mac/`)

| File | Description |
|------|-------------|
| `cloudx-agent-install.sh` | Installs the agent on macOS utilizing native package management. |
| `install.sh` | Alternative installation script (legacy). |
| `cloudx-agent-uninstall.sh` | Uninstalls the agent from macOS. |
| `cloudx-agent-setup.sh` | Post-install configuration for macOS environments. |
| `remove-threat.py` | Python script for automated threat removal and remediation (shared with Linux). |
| `requirements.txt` | Python dependencies for `remove-threat.py`. |

---

## 3. System Monitor (`/api/system-monitor`)

The backend provides a lightweight endpoint to monitor system resources of the host or a remote target.

### Endpoint: `GET /api/system-monitor?target=<ip>`

-   **Local Monitoring (`localhost`)**:
    -   Uses `psutil` to gather real-time metrics from the server running the backend.
    -   **Metrics**: CPU usage (%), Memory usage (%), Disk usage (%).
    -   **Response**: JSON object with historical data points (simulated for stateless request) and "spike" flags if usage > 80%.

-   **Remote Monitoring**:
    -   Uses `ping3` to check latency to the target IP.
    -   **Metrics**: Network Latency (ms).
    -   **Agentless Mode**: Returns `is_agentless: True` to indicate limited visibility compared to a full agent install.

---

## 4. Network Scanners Module (`scanners/network_scanners.py`)

The backend provides a unified scanning interface supporting multiple network scanning tools.

### Supported Tools

| Tool | Function | Description |
|------|----------|-------------|
| **Nmap** | `_run_nmap_scan()` | Comprehensive network discovery and security auditing. Supports multiple scan types. |
| **ZMap** | `_run_zmap_scan()` | High-speed internet-wide network scanner. Optimized for large-scale scans. |
| **Masscan** | `_run_masscan_scan()` | Fast port scanner capable of scanning the entire internet in under 6 minutes. |

### Main Entry Point

```python
def run_scan(tool, target, scan_type='default', port=None):
    """
    Unified scan interface that dispatches to the appropriate scanner.
    
    Args:
        tool: 'nmap', 'zmap', or 'masscan'
        target: IP address or CIDR range to scan
        scan_type: Scan configuration (varies by tool)
        port: Optional specific port to scan
    
    Yields:
        Progress updates and final scan results
    """
```

### Scan Types

#### Nmap Scan Types
- `default`: Standard service detection
- `quick`: Fast scan of common ports
- `full`: Comprehensive scan with OS detection
- `vuln`: Vulnerability scanning

#### ZMap/Masscan Scan Types
- `tcp_syn`: TCP SYN scan (default)
- `tcp_scan`: Full TCP connection scan

### Output Format

Scan results are returned as JSON with the following structure:
```json
{
  "type": "result",
  "value": {
    "hosts": [...],
    "ports": [...],
    "services": [...],
    "scan_info": {...}
  }
}
```

### Notes

- Network scanners require elevated privileges (root/Administrator) to access raw sockets.
- ZMap and Masscan are optimized for speed but may be less detailed than Nmap.
- All scanners support real-time progress updates via generator yields.
