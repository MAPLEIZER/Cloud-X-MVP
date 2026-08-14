#!/usr/bin/env python3
"""Cloud-X Wazuh active response: validated threat quarantine."""

import datetime
import hashlib
import json
import mimetypes
import os
import platform
import secrets
import shutil
import stat
import subprocess
import sys

import psutil

WAZUH_MANAGER = os.getenv("WAZUH_MANAGER", "configured-manager")
AGENT_NAME = platform.node()
MAX_INPUT_BYTES = 1024 * 1024
MAX_PATH_LENGTH = 4096

if os.name == "nt":
    LOG_FILE = r"C:\Program Files (x86)\ossec-agent\active-response\active-responses.log"
    QUARANTINE_DIR = os.path.join(
        os.environ.get("ProgramData", r"C:\ProgramData"), "CloudX", "Quarantine"
    )
    DEFAULT_SAFE_DIRS = [
        os.path.expandvars(r"%USERPROFILE%\Downloads"),
        os.path.expandvars(r"%TEMP%"),
        os.path.expandvars(r"%PUBLIC%\Downloads"),
    ]
else:
    LOG_FILE = "/var/ossec/logs/active-responses.log"
    QUARANTINE_DIR = "/var/ossec/quarantine/cloudx"
    DEFAULT_SAFE_DIRS = [
        os.path.expanduser("~/Downloads"),
        "/tmp",
        "/var/tmp",
    ]

SAFE_DIRS = [
    item
    for item in os.getenv("CLOUDX_SAFE_DIRS", os.pathsep.join(DEFAULT_SAFE_DIRS)).split(os.pathsep)
    if item
]

ADD_COMMAND = 0
DELETE_COMMAND = 1
CONTINUE_COMMAND = 2
ABORT_COMMAND = 3
OS_SUCCESS = 0
OS_INVALID = -1


class Message:
    def __init__(self):
        self.alert = {}
        self.command = OS_INVALID


def _safe_log_text(value, limit=2048):
    text = str(value).replace("\r", "\\r").replace("\n", "\\n")
    return text[:limit]


def write_structured_log(action_data):
    try:
        log_entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "agent": AGENT_NAME,
            "manager": WAZUH_MANAGER,
            **action_data,
        }
        with open(LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(json.dumps(log_entry, ensure_ascii=True) + "\n")
    except OSError as exc:
        print(f"Could not write active-response log: {_safe_log_text(exc)}", file=sys.stderr)


def write_log(ar_name, msg, level="INFO"):
    try:
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y/%m/%d %H:%M:%S UTC")
        with open(LOG_FILE, "a", encoding="utf-8") as log_file:
            log_file.write(
                f"{timestamp} [{_safe_log_text(level, 16)}] "
                f"{_safe_log_text(ar_name, 256)}: {_safe_log_text(msg)}\n"
            )
    except OSError as exc:
        print(f"Could not write active-response log: {_safe_log_text(exc)}", file=sys.stderr)


def _read_limited(handle):
    data = handle.read(MAX_INPUT_BYTES + 1)
    if len(data) > MAX_INPUT_BYTES:
        raise ValueError("active-response input exceeds size limit")
    return data


def validate_input(alert_file=None):
    message = Message()
    try:
        if alert_file:
            if os.getenv("CLOUDX_ALLOW_ALERT_FILE") != "1":
                raise ValueError("--alert-file is disabled unless CLOUDX_ALLOW_ALERT_FILE=1")
            with open(alert_file, "r", encoding="utf-8") as handle:
                input_str = _read_limited(handle)
        else:
            input_str = sys.stdin.readline(MAX_INPUT_BYTES + 1)
            if len(input_str) > MAX_INPUT_BYTES:
                raise ValueError("active-response input exceeds size limit")
        data = json.loads(input_str)
        if not isinstance(data, dict):
            raise ValueError("active-response input must be a JSON object")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        write_log(sys.argv[0] if sys.argv else "remove-threat", f"Invalid input: {exc}", "ERROR")
        return message

    command = str(data.get("command", "")).lower()
    if command == "add":
        message.command = ADD_COMMAND
    elif command == "delete":
        message.command = DELETE_COMMAND
    else:
        write_log(sys.argv[0], "Invalid active-response command", "ERROR")
        return message

    message.alert = data
    return message


def send_keys_and_check(keys):
    keys_msg = json.dumps(
        {
            "version": 1,
            "origin": {"name": sys.argv[0], "module": "active-response"},
            "command": "check_keys",
            "parameters": {"keys": keys},
        }
    )
    print(keys_msg)
    sys.stdout.flush()

    try:
        input_str = sys.stdin.readline(MAX_INPUT_BYTES + 1)
        if len(input_str) > MAX_INPUT_BYTES:
            raise ValueError("manager response exceeds size limit")
        data = json.loads(input_str)
        action = str(data.get("command", "")).lower()
        if action == "continue":
            return CONTINUE_COMMAND
        if action == "abort":
            return ABORT_COMMAND
    except (ValueError, json.JSONDecodeError) as exc:
        write_log(sys.argv[0], f"Invalid manager response: {exc}", "ERROR")
    return OS_INVALID


def verify_digital_signature(file_path):
    if os.name != "nt":
        return True

    command = [
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        (
            "& { param([string]$Path) "
            "(Get-AuthenticodeSignature -LiteralPath $Path).Status.ToString() }"
        ),
        file_path,
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        status = result.stdout.strip()
        return result.returncode == 0 and status == "Valid"
    except (OSError, subprocess.SubprocessError) as exc:
        write_log(sys.argv[0], f"Signature verification failed: {exc}", "ERROR")
        return False


def verify_file_type(file_path):
    try:
        mime_type, _ = mimetypes.guess_type(file_path)
        with open(file_path, "rb") as handle:
            header = handle.read(16)
        signatures = {
            b"MZ": "PE executable",
            b"\x7fELF": "ELF executable",
            b"\xca\xfe\xba\xbe": "Mach-O executable",
            b"PK": "ZIP/JAR archive",
        }
        for signature, description in signatures.items():
            if header.startswith(signature):
                return description
        return mime_type or "unknown"
    except OSError as exc:
        write_log(sys.argv[0], f"File type check failed: {exc}", "ERROR")
        return "unknown"


def _path_is_within(path, root):
    try:
        candidate = os.path.normcase(os.path.abspath(path))
        safe_root = os.path.normcase(os.path.abspath(root))
        return os.path.commonpath([candidate, safe_root]) == safe_root
    except (ValueError, OSError):
        return False


def resolve_safe_file(path_to_check):
    if not isinstance(path_to_check, str) or not path_to_check or len(path_to_check) > MAX_PATH_LENGTH:
        return None
    if "\x00" in path_to_check:
        return None

    try:
        if os.path.islink(path_to_check):
            return None
        resolved = os.path.realpath(path_to_check)
        info = os.stat(resolved, follow_symlinks=False)
        if not stat.S_ISREG(info.st_mode):
            return None

        safe_roots = [os.path.realpath(root) for root in SAFE_DIRS if root]
        if not any(_path_is_within(resolved, root) for root in safe_roots):
            return None

        return resolved, (info.st_dev, info.st_ino)
    except OSError:
        return None


def _same_file_identity(file_path, expected_identity):
    try:
        info = os.stat(file_path, follow_symlinks=False)
        return (info.st_dev, info.st_ino) == expected_identity and stat.S_ISREG(info.st_mode)
    except OSError:
        return False


def calculate_hash(file_path):
    try:
        digest = hashlib.sha256()
        with open(file_path, "rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError as exc:
        write_log(sys.argv[0], f"Hash calculation failed: {exc}", "ERROR")
        return None


def kill_malicious_processes(file_path):
    killed = []

    def kill_tree(pid):
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            for child in children:
                try:
                    child.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            try:
                parent.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            _, alive = psutil.wait_procs([parent, *children], timeout=3)
            for process in alive:
                try:
                    process.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            killed.extend([process.pid for process in [parent, *children]])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    for process in psutil.process_iter(["pid", "exe"]):
        try:
            executable = process.info.get("exe")
            if executable and os.path.samefile(executable, file_path):
                kill_tree(process.info["pid"])
        except (OSError, psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return sorted(set(killed))


def _prepare_quarantine_dir():
    os.makedirs(QUARANTINE_DIR, mode=0o700, exist_ok=True)
    if os.name != "nt":
        os.chmod(QUARANTINE_DIR, 0o700)


def quarantine_file(file_path, expected_identity, rule_id, dry_run=False):
    if not _same_file_identity(file_path, expected_identity):
        write_structured_log(
            {"file": file_path, "rule_id": rule_id, "action": "file_changed", "status": "blocked"}
        )
        return False

    file_hash = calculate_hash(file_path)
    file_type = verify_file_type(file_path)
    signature_valid = True
    if file_type and "executable" in file_type.lower():
        signature_valid = verify_digital_signature(file_path)

    if dry_run:
        write_structured_log(
            {
                "file": file_path,
                "hash": file_hash,
                "rule_id": rule_id,
                "action": "dry_run",
                "file_type": file_type,
                "processes_terminated": [],
                "signature_valid": signature_valid,
                "status": "success",
            }
        )
        return True

    killed_pids = kill_malicious_processes(file_path)
    if not _same_file_identity(file_path, expected_identity):
        write_structured_log(
            {"file": file_path, "rule_id": rule_id, "action": "file_changed", "status": "blocked"}
        )
        return False

    try:
        _prepare_quarantine_dir()
        token = secrets.token_hex(8)
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
        destination = os.path.join(
            QUARANTINE_DIR,
            f"{timestamp}_{token}_{os.path.basename(file_path)}",
        )
        shutil.move(file_path, destination)
        if os.name != "nt":
            os.chmod(destination, 0o600)

        metadata = {
            "original_path": file_path,
            "quarantine_path": destination,
            "file_hash": file_hash,
            "file_type": file_type,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "killed_processes": killed_pids,
            "rule_id": rule_id,
            "signature_valid": signature_valid,
        }
        metadata_path = destination + ".metadata.json"
        with open(metadata_path, "x", encoding="utf-8") as handle:
            json.dump(metadata, handle, indent=2, ensure_ascii=True)
        if os.name != "nt":
            os.chmod(metadata_path, 0o600)

        write_structured_log(
            {
                "file": file_path,
                "hash": file_hash,
                "rule_id": rule_id,
                "action": "quarantine",
                "quarantine_path": destination,
                "file_type": file_type,
                "processes_terminated": killed_pids,
                "signature_valid": signature_valid,
                "status": "success",
            }
        )
        return True
    except OSError as exc:
        write_structured_log(
            {
                "file": file_path,
                "hash": file_hash,
                "rule_id": rule_id,
                "action": "quarantine_failed",
                "error": _safe_log_text(exc),
                "status": "error",
            }
        )
        return False


def _extract_alert_file(alert):
    virustotal = alert.get("data", {}).get("virustotal", {})
    if isinstance(virustotal, dict):
        source = virustotal.get("source", {})
        if isinstance(source, dict) and source.get("file"):
            return source.get("file")

    syscheck = alert.get("syscheck", {})
    if isinstance(syscheck, dict) and syscheck.get("path"):
        return syscheck.get("path")

    data = alert.get("data", {})
    if isinstance(data, dict):
        return data.get("file")
    return None


def main():
    dry_run = "--dry-run" in sys.argv
    alert_file = None
    if "--alert-file" in sys.argv:
        try:
            alert_file = sys.argv[sys.argv.index("--alert-file") + 1]
        except (ValueError, IndexError):
            return OS_INVALID

    message = validate_input(alert_file)
    if message.command < 0:
        return OS_INVALID
    if message.command == DELETE_COMMAND:
        return OS_SUCCESS

    alert = message.alert.get("parameters", {}).get("alert", {})
    if not isinstance(alert, dict):
        return OS_INVALID

    rule_id = str(alert.get("rule", {}).get("id", ""))
    if not rule_id or len(rule_id) > 64:
        return OS_INVALID

    if not dry_run:
        action = send_keys_and_check([rule_id])
        if action == ABORT_COMMAND:
            return OS_SUCCESS
        if action != CONTINUE_COMMAND:
            return OS_INVALID

    file_path = _extract_alert_file(alert)
    safe_file = resolve_safe_file(file_path)
    if not safe_file:
        write_structured_log(
            {
                "file": _safe_log_text(file_path, 1024),
                "rule_id": rule_id,
                "action": "blocked_unsafe_path",
                "status": "security_violation",
            }
        )
        return OS_INVALID

    resolved_path, identity = safe_file
    return OS_SUCCESS if quarantine_file(resolved_path, identity, rule_id, dry_run) else OS_INVALID


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        write_log(
            sys.argv[0] if sys.argv else "remove-threat",
            f"Unhandled exception: {exc}",
            "ERROR",
        )
        sys.exit(OS_INVALID)
