#!/usr/bin/python3
# Copyright (C) 2023, Cloud-X Security
# All rights reserved.
# Wazuh Active Response Script - Threat Removal and Quarantine
# GitHub: https://github.com/MAPLEIZER/Cloud-X-security-agent
# Usage: 
#   Download and deploy to: C:\Program Files (x86)\ossec-agent\active-response\bin\remove-threat.py
#   Or use the automated installer which handles deployment automatically

import os
import sys
import json
import datetime
import shutil
import hashlib
import subprocess
import psutil
import stat
import platform
import mimetypes
from pathlib import Path

# Wazuh Manager Configuration
WAZUH_MANAGER = "192.168.100.37"
AGENT_NAME = platform.node()  # Dynamic agent name based on hostname

# Cross-platform log file location
if os.name == 'nt':
    LOG_FILE = "C:\\Program Files (x86)\\ossec-agent\\active-response\\active-responses.log"
    QUARANTINE_DIR = os.path.expandvars("%TEMP%\\wazuh_quarantine")
    SAFE_DIRS = [
        os.path.expandvars("%USERPROFILE%\\Downloads"),
        os.path.expandvars("%TEMP%"),
        os.path.expandvars("%PUBLIC%\\Downloads")
    ]
else:
    LOG_FILE = "/var/ossec/logs/active-responses.log"
    QUARANTINE_DIR = "/tmp/wazuh_quarantine"
    SAFE_DIRS = [
        os.path.expanduser("~/Downloads"),
        "/tmp",
        "/var/tmp"
    ]

# Command constants
ADD_COMMAND = 0
DELETE_COMMAND = 1
CONTINUE_COMMAND = 2
ABORT_COMMAND = 3

# Exit codes
OS_SUCCESS = 0
OS_INVALID = -1

# Data structure to hold alert information and command type
class Message:
    def __init__(self):
        self.alert = {}
        self.command = OS_INVALID

# Structured JSON logging for SIEM integration
def write_structured_log(action_data):
    """Write structured JSON log entry for server-side processing"""
    try:
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "agent": AGENT_NAME,
            "manager": WAZUH_MANAGER,
            **action_data
        }
        
        # Write to Wazuh log file
        with open(LOG_FILE, "a") as log_file:
            log_file.write(json.dumps(log_entry) + "\n")
            
    except IOError as e:
        print(f"Could not write to log file {LOG_FILE}: {e}")

# Legacy logging function for compatibility
def write_log(ar_name, msg, level="INFO"):
    try:
        timestamp = datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')
        with open(LOG_FILE, "a") as log_file:
            log_file.write(f"{timestamp} [{level}] {ar_name}: {msg}\n")
    except IOError as e:
        print(f"Could not write to log file {LOG_FILE}: {e}")

# Validates and parses the JSON alert sent from the Wazuh manager via stdin
def validate_input(alert_file=None):
    """Validates and parses JSON alert from file or stdin"""
    try:
        input_str = ""
        if alert_file:
            with open(alert_file, 'r') as f:
                input_str = f.read()
        else:
            for line in sys.stdin:
                input_str = line
                break
        data = json.loads(input_str)
    except (ValueError, json.JSONDecodeError) as e:
        write_log(sys.argv[0], f"Failed to decode JSON from stdin: {e}", "ERROR")
        # Return a message with an invalid command if parsing fails.
        m = Message()
        m.command = OS_INVALID
        return m

    m = Message()
    m.alert = data
    command = data.get("command", "").lower()

    if command == "add":
        m.command = ADD_COMMAND
    elif command == "delete":
        m.command = DELETE_COMMAND
    else:
        write_log(sys.argv[0], f"Invalid command: {command}", "ERROR")
        m.command = OS_INVALID
    return m

# Sends keys to Wazuh manager for validation
def send_keys_and_check(keys):
    keys_msg = json.dumps({
        "version": 1,
        "origin": {"name": sys.argv[0], "module": "active-response"},
        "command": "check_keys",
        "parameters": {"keys": keys}
    })
    
    write_log(sys.argv[0], keys_msg)
    print(keys_msg)
    sys.stdout.flush()

    try:
        input_str = ""
        while True:
            line = sys.stdin.readline()
            if line:
                input_str = line
                break
        
        data = json.loads(input_str)
        action = data.get("command", "").lower()
        
        if action == "continue":
            return CONTINUE_COMMAND
        elif action == "abort":
            return ABORT_COMMAND
        else:
            write_log(sys.argv[0], f"Invalid response: {action}", "ERROR")
            return OS_INVALID
    except Exception as e:
        write_log(sys.argv[0], f"Failed to parse response: {e}", "ERROR")
        return OS_INVALID

# Verify digital signature of executable files (Windows only)
def verify_digital_signature(file_path):
    if os.name != 'nt':
        return True  # Skip on non-Windows systems
    
    try:
        result = subprocess.run([
            'powershell', '-Command',
            f'Get-AuthenticodeSignature "{file_path}" | Select-Object -ExpandProperty Status'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            status = result.stdout.strip()
            if status in ['Valid', 'UnknownError']:  # UnknownError can be valid for some system files
                return True
            else:
                write_log(sys.argv[0], f"Invalid signature for {file_path}: {status}", "WARNING")
                return False
    except Exception as e:
        write_log(sys.argv[0], f"Signature verification error: {e}", "ERROR")
    return False

# Verify file type using magic bytes, not just extension
def verify_file_type(file_path):
    try:
        # Get MIME type
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # Read first few bytes to verify file signature
        with open(file_path, 'rb') as f:
            header = f.read(16)
        
        # Common executable signatures
        exe_signatures = {
            b'MZ': 'PE executable',
            b'\x7fELF': 'ELF executable',
            b'\xca\xfe\xba\xbe': 'Mach-O executable',
            b'PK': 'ZIP/JAR archive'
        }
        
        for sig, desc in exe_signatures.items():
            if header.startswith(sig):
                write_log(sys.argv[0], f"File type detected: {desc} for {file_path}")
                return desc
        
        return mime_type or 'unknown'
    except Exception as e:
        write_log(sys.argv[0], f"File type verification error: {e}", "ERROR")
        return 'unknown'

# Verify file ownership and permissions
def verify_file_ownership(file_path):
    try:
        file_stat = os.stat(file_path)
        
        # Check if file is world-writable (security risk)
        if file_stat.st_mode & stat.S_IWOTH:
            write_log(sys.argv[0], f"Security risk: World-writable file {file_path}", "WARNING")
            return False
        
        # On Windows, check if file is owned by system or current user
        if os.name == 'nt':
            try:
                import win32security
                import win32api
                
                sd = win32security.GetFileSecurity(file_path, win32security.OWNER_SECURITY_INFORMATION)
                owner_sid = sd.GetSecurityDescriptorOwner()
                name, domain, type = win32security.LookupAccountSid(None, owner_sid)
                
                write_log(sys.argv[0], f"File owner: {domain}\\{name}")
                return True
            except ImportError:
                write_log(sys.argv[0], "pywin32 not available for ownership check", "INFO")
                return True
        
        return True
    except Exception as e:
        write_log(sys.argv[0], f"Ownership verification error: {e}", "ERROR")
        return False

# Kill malicious processes with recursive child termination
def kill_malicious_processes(file_path):
    """Terminate processes and their children recursively"""
    try:
        killed_processes = []
        file_name = os.path.basename(file_path)
        
        def kill_process_tree(pid):
            """Recursively kill process and all children"""
            try:
                parent = psutil.Process(pid)
                children = parent.children(recursive=True)
                
                # Kill children first
                for child in children:
                    try:
                        child.terminate()
                        killed_processes.append(child.pid)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                # Kill parent
                parent.terminate()
                killed_processes.append(pid)
                
                # Wait for graceful termination
                gone, still_alive = psutil.wait_procs([parent] + children, timeout=3)
                
                # Force kill if still alive
                for proc in still_alive:
                    try:
                        proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Find and terminate processes using the malicious file
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                if proc.info['exe'] and os.path.samefile(proc.info['exe'], file_path):
                    kill_process_tree(proc.info['pid'])
                elif proc.info['name'] and proc.info['name'].lower() == file_name.lower():
                    kill_process_tree(proc.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
                continue
            
        return killed_processes
    except Exception as e:
        write_log(sys.argv[0], f"Process termination error: {e}", "ERROR")
        return []

# Enable PowerShell logging (integrate PowerShell script functionality)
def enable_powershell_logging():
    if os.name != 'nt':
        return True
    
    try:
        ps_script = '''
        $basePath = "HKLM:\SOFTWARE\Policies\Microsoft\Windows\PowerShell\ScriptBlockLogging"
        if (!(Test-Path $basePath)) {
            New-Item -Path $basePath -Force | Out-Null
        }
        Set-ItemProperty -Path $basePath -Name "EnableScriptBlockLogging" -Value 1 -Type DWord
        Write-Output "PowerShell logging enabled"
        '''
        
        result = subprocess.run(['powershell', '-Command', ps_script], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            write_log(sys.argv[0], "PowerShell script block logging enabled")
            return True
        else:
            write_log(sys.argv[0], f"Failed to enable PowerShell logging: {result.stderr}", "ERROR")
            return False
    except Exception as e:
        write_log(sys.argv[0], f"PowerShell logging setup error: {e}", "ERROR")
        return False

# Check if file path is in safe directories with enhanced security
def is_safe_path(path_to_check):
    try:
        abs_path = os.path.abspath(path_to_check)
        
        # Block symbolic links
        if os.path.islink(abs_path):
            write_log(sys.argv[0], f"Blocked symlink: {path_to_check}", "WARNING")
            return False
        
        # Verify file ownership and permissions
        if not verify_file_ownership(abs_path):
            write_log(sys.argv[0], f"File ownership/permissions check failed: {path_to_check}", "WARNING")
            return False
        
        # Check if path is in safe directories
        is_safe = any(abs_path.startswith(os.path.abspath(d)) for d in SAFE_DIRS)
        
        if not is_safe:
            write_log(sys.argv[0], f"Blocked unsafe path: {path_to_check}", "WARNING")
            return False
            
        return True
    except Exception as e:
        write_log(sys.argv[0], f"Path safety check error: {e}", "ERROR")
        return False
    try:
        abs_path = os.path.abspath(path_to_check)
        
        # Block symbolic links
        if os.path.islink(abs_path):
            write_log(sys.argv[0], f"Blocked symlink: {path_to_check}", "WARNING")
            write_log(sys.argv[0], f"Blocked symlink: {file_path}", "WARNING")
            return False
        
        # Verify file ownership and permissions
        if not verify_file_ownership(abs_path):
            write_log(sys.argv[0], f"File ownership/permissions check failed: {file_path}", "WARNING")
            return False
        
        # Check if path is in safe directories
        is_safe = any(abs_path.startswith(os.path.abspath(d)) for d in SAFE_DIRS)
        
        if not is_safe:
            write_log(sys.argv[0], f"File outside safe directories: {file_path}", "WARNING")
            
        return is_safe
    except Exception as e:
        write_log(sys.argv[0], f"Path validation error: {e}", "ERROR")
        return False

# Calculate SHA256 hash of file
def calculate_hash(file_path):
    try:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except (IOError, OSError) as e:
        write_log(sys.argv[0], f"Hash calculation error: {e}", "ERROR")
        return None

# Lightweight quarantine with structured logging
def quarantine_file(file_path, rule_id, dry_run=False):
    """Fast, minimal quarantine with structured JSON logging"""
    if not os.path.exists(file_path):
        write_structured_log({
            "file": file_path,
            "rule_id": rule_id,
            "action": "file_not_found",
            "status": "warning"
        })
        return

    # Fast security checks
    file_hash = calculate_hash(file_path)
    file_type = verify_file_type(file_path)
    
    # Terminate processes first (critical for containment)
    killed_pids = kill_malicious_processes(file_path)
    
    # Check digital signature only for executables (performance optimization)
    signature_valid = True
    if file_type and 'executable' in file_type.lower():
        signature_valid = verify_digital_signature(file_path)

    if dry_run:
        write_structured_log({
            "file": file_path,
            "hash": file_hash,
            "rule_id": rule_id,
            "action": "dry_run",
            "file_type": file_type,
            "processes_terminated": killed_pids,
            "signature_valid": signature_valid
        })
        return

    try:
        # Fast quarantine operation
        os.makedirs(QUARANTINE_DIR, exist_ok=True)
        dest_name = f"{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{os.path.basename(file_path)}"
        dest_path = os.path.join(QUARANTINE_DIR, dest_name)
        
        shutil.move(file_path, dest_path)
        
        # Structured JSON log for server processing
        write_structured_log({
            "file": file_path,
            "hash": file_hash,
            "rule_id": rule_id,
            "action": "quarantine",
            "quarantine_path": dest_path,
            "file_type": file_type,
            "processes_terminated": killed_pids,
            "signature_valid": signature_valid,
            "status": "success"
        })
        
        # Minimal metadata for forensics
        metadata = {
            "original_path": file_path,
            "quarantine_path": dest_path,
            "file_hash": file_hash,
            "file_type": file_type,
            "timestamp": datetime.datetime.now().isoformat(),
            "killed_processes": killed_pids,
            "rule_id": rule_id
        }
        
        metadata_path = dest_path + ".metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
            
    except (OSError, IOError) as e:
        write_structured_log({
            "file": file_path,
            "hash": file_hash,
            "rule_id": rule_id,
            "action": "quarantine_failed",
            "error": str(e),
            "status": "error"
        })

# Main function with enhanced security features
def main():
    write_log(sys.argv[0], "Cloud-X Security Threat Response Started")
    
    # Enable PowerShell logging on Windows
    if os.name == 'nt':
        enable_powershell_logging()
    
    dry_run = '--dry-run' in sys.argv
    alert_file = None
    if '--alert-file' in sys.argv:
        try:
            alert_file_index = sys.argv.index('--alert-file') + 1
            if alert_file_index < len(sys.argv):
                alert_file = sys.argv[alert_file_index]
        except (ValueError, IndexError):
            pass

    if dry_run:
        write_log(sys.argv[0], "Dry run mode enabled")
    
    # Validate input
    msg = validate_input(alert_file)
    if msg.command < 0:
        sys.exit(OS_INVALID)

    if msg.command == ADD_COMMAND:
        alert = msg.alert.get("parameters", {}).get("alert", {})
        if not alert:
            write_log(sys.argv[0], "Alert data missing", "ERROR")
            sys.exit(OS_INVALID)

        rule_id = alert.get("rule", {}).get("id")
        if not rule_id:
            write_log(sys.argv[0], "Rule ID missing", "ERROR")
            sys.exit(OS_INVALID)

        # Check with manager (skip in dry-run mode for testing)
        action = CONTINUE_COMMAND
        if not dry_run:
            action = send_keys_and_check([rule_id])

        if action != CONTINUE_COMMAND:
            if action == ABORT_COMMAND:
                write_log(sys.argv[0], "Aborted by manager")
            sys.exit(OS_SUCCESS if action == ABORT_COMMAND else OS_INVALID)

        # Get file path from alert (support multiple sources)
        file_path = None
        
        # Try VirusTotal data first
        vt_data = alert.get("data", {}).get("virustotal", {})
        if vt_data:
            file_path = vt_data.get("source", {}).get("file")
        
        # Fallback to syscheck data
        if not file_path:
            syscheck_data = alert.get("syscheck", {})
            if syscheck_data:
                file_path = syscheck_data.get("path")
        
        # Fallback to general data field
        if not file_path:
            file_path = alert.get("data", {}).get("file")
        
        if not file_path:
            write_log(sys.argv[0], "File path not found in alert", "ERROR")
            sys.exit(OS_INVALID)

        # Fast path validation and quarantine
        if is_safe_path(file_path):
            quarantine_file(os.path.abspath(file_path), rule_id, dry_run)
        else:
            write_structured_log({
                "file": file_path,
                "rule_id": rule_id,
                "action": "blocked_unsafe_path",
                "status": "security_violation"
            })

    write_log(sys.argv[0], "Cloud-X Security Threat Response Completed")
    sys.exit(OS_SUCCESS)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        write_log(sys.argv[0] if sys.argv else "ThreatResponse", f"Unhandled exception: {e}", "ERROR")
        sys.exit(OS_INVALID)
