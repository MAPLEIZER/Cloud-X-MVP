# Cloud-X Security - Advanced Wazuh Agent Integration

This package provides enterprise-grade threat response capabilities for Wazuh agents with advanced security features.

## Features

This solution provides a multi-layered security approach, combining automated setup with a powerful active response engine.

### ⚙️ Automated Setup & Hardening
- **Sysmon Integration**: Deploys Sysmon for unparalleled visibility into system activity.
- **Advanced Windows Auditing**: Enables granular logging for high-value security events.
- **PowerShell Monitoring**: Captures script blocks and module loads to detect in-memory threats.
- **Osquery Integration**: The agent configuration enables osquery for rich, queryable endpoint telemetry.
- **Security Configuration Assessment (SCA)**: The agent is pre-configured to detect configuration drifts from security benchmarks.

### 🛡️ Advanced Active Response (`remove-threat.py`)
- **Digital Signature Verification**: Validates executable signatures before taking action.
- **File Type Verification**: Uses magic bytes, not just extensions, to identify true file types.
- **Process Termination**: Automatically finds and kills malicious processes associated with a threat.
- **Enhanced Quarantine**: Moves threats to a safe, timestamped location with full metadata for analysis.
- **Security Hardening**: Includes built-in protection against symlink and path traversal attacks.

## Installation

### Automatic Setup
The `post-install-setup.ps1` script automates the configuration of advanced security and monitoring features on Windows agents. Run it as an Administrator after the Wazuh agent installation is complete.

```powershell
# Run as Administrator
.\post-install-setup.ps1
```

The script performs the following actions:
- **Installs Sysmon**: Downloads, installs, and configures Sysmon with the SwiftOnSecurity configuration file for deep process and network monitoring.
- **Enables Advanced Auditing**: Sets detailed audit policies (`auditpol`) to log critical security events related to file access, process creation, and handle manipulation.
- **Activates PowerShell Logging**: Modifies the registry to enable PowerShell Module Logging and Script Block Logging, capturing commands and script content to detect fileless attacks.
- **Sets Up Active Response**: Deploys the necessary active response scripts and ensures Python dependencies are installed.

### Manual Installation

1. **Copy Scripts**:
   ```bash
   cp wazuh-configs/scripts/remove-threat.py /var/ossec/active-response/bin/
   # or on Windows:
   copy wazuh-configs\scripts\remove-threat.py "C:\Program Files (x86)\ossec-agent\active-response\bin\"
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Wazuh Manager**:
   Add the following to your `ossec.conf`:

   ```xml
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
   ```

## Configuration

### Safe Directories
The script only operates on files within predefined safe directories:

**Windows**:
- `%USERPROFILE%\Downloads`
- `%TEMP%`
- `%PUBLIC%\Downloads`

**Linux**:
- `~/Downloads`
- `/tmp`
- `/var/tmp`

### Quarantine Location
- **Windows**: `%TEMP%\wazuh_quarantine`
- **Linux**: `/tmp/wazuh_quarantine`

## Usage

### Testing
Use dry-run mode to test without making changes:
```bash
python remove-threat.py --dry-run
```

### Monitoring
Check logs at:
- **Windows**: `C:\Program Files (x86)\ossec-agent\active-response\active-responses.log`
- **Linux**: `/var/ossec/logs/active-responses.log`

## Rule IDs

The system responds to these Wazuh rule IDs:
- **100543**: Malicious PowerShell commands
- **100546**: PowerShell obfuscation detection
- **100547**: In-memory download and execution

## Security Features

### Digital Signature Verification
Automatically verifies digital signatures on Windows executables using PowerShell's `Get-AuthenticodeSignature`.

### File Type Detection
Uses magic bytes to verify actual file types:
- PE executables (`MZ` header)
- ELF executables (`\x7fELF` header)
- Mach-O executables
- ZIP/JAR archives

### Process Management
- Identifies running processes using the malicious file
- Gracefully terminates processes before quarantine
- Force-kills processes if graceful termination fails

### Metadata Tracking
Each quarantined file includes a `.metadata.json` file with:
- Original file path
- SHA256 hash
- File type information
- Timestamp
- Terminated process IDs

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure the script runs with appropriate privileges
2. **Python Dependencies**: Install `psutil` and `pywin32` (Windows only)
3. **PowerShell Execution Policy**: May need to adjust execution policy on Windows

### Log Analysis
Monitor the active response log for detailed execution information including:
- File quarantine operations
- Security check results
- Process termination activities
- Error conditions

## Support

For issues or questions regarding Cloud-X Security integration, check the logs and ensure all dependencies are properly installed.
