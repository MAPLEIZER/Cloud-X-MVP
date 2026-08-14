import logging
import os
import re
import shutil
import subprocess
import threading
import time
from queue import Empty, Queue

import xmltodict

from security_utils import is_valid_scan_target

logger = logging.getLogger(__name__)


def enqueue_output(out, queue):
    try:
        with out:
            for line in iter(out.readline, ""):
                queue.put(line)
    finally:
        queue.put(None)


def _require_executable(name):
    path = shutil.which(name)
    if not path:
        return None, f"{name} is not installed or not in PATH."
    if not os.access(path, os.X_OK):
        return None, f"{name} is not executable."
    return path, None


def _terminate_process(proc):
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _cancel_requested(cancel_check):
    return bool(cancel_check and cancel_check())


def _run_nmap_scan(target, scan_type="default", port=None, cancel_check=None):
    del port

    if not is_valid_scan_target(target):
        yield {"type": "error", "value": "Invalid scan target."}
        return

    scan_args = {
        "default": ["-T4", "-F"],
        "quick": ["-T4", "-F"],
        "intense": ["-T4", "-A", "-v"],
        "tcp": ["-p", "1-65535"],
        "udp": ["-sU", "-T4"],
    }
    arguments = scan_args.get(scan_type)
    if arguments is None:
        yield {"type": "error", "value": "Unsupported Nmap scan type."}
        return

    nmap_path, error = _require_executable("nmap")
    if error:
        yield {"type": "error", "value": error}
        return

    command = [nmap_path, *arguments, "-v", "-oX", "-", target]
    logger.info("Starting Nmap scan for validated target %s", target)

    try:
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, PermissionError):
        logger.exception("Failed to start Nmap")
        yield {"type": "error", "value": "Failed to start Nmap."}
        return

    yield {"type": "process", "value": proc}

    progress_queue = Queue()
    threading.Thread(
        target=enqueue_output,
        args=(proc.stderr, progress_queue),
        daemon=True,
    ).start()

    start_time = time.monotonic()
    timeout = 300

    try:
        while proc.poll() is None:
            if _cancel_requested(cancel_check):
                logger.info("Nmap scan canceled")
                _terminate_process(proc)
                yield {"type": "cancelled", "value": "Scan canceled."}
                return
            if time.monotonic() - start_time > timeout:
                logger.warning("Nmap scan timed out")
                _terminate_process(proc)
                yield {"type": "error", "value": "Nmap scan timed out after 5 minutes."}
                return

            try:
                line = progress_queue.get(timeout=0.1)
                if line is None:
                    continue
                match = re.search(r"About (\d+(?:\.\d+)?)% done", line)
                if match:
                    yield {"type": "progress", "value": int(float(match.group(1)))}
            except Empty:
                continue

        stdout_data, stderr_data = proc.communicate()

        if proc.returncode != 0:
            logger.warning(
                "Nmap failed with return code %s: %s",
                proc.returncode,
                stderr_data[-1000:],
            )
            yield {"type": "error", "value": "Nmap scan failed."}
            return

        if not stdout_data.strip():
            yield {"type": "error", "value": "Nmap returned no XML output."}
            return

        try:
            json_output = xmltodict.parse(stdout_data)
        except Exception:
            logger.exception("Failed to parse Nmap XML")
            yield {"type": "error", "value": "Failed to parse Nmap output."}
            return

        yield {"type": "result", "value": json_output}
    finally:
        if proc.poll() is None:
            _terminate_process(proc)


def _run_zmap_scan(target, scan_type="tcp_syn", port=None, cancel_check=None):
    if not is_valid_scan_target(target):
        yield {"type": "error", "value": "Invalid scan target."}
        return

    zmap_path, error = _require_executable("zmap")
    if error:
        yield {"type": "error", "value": error}
        return

    command = [zmap_path]
    if scan_type == "tcp_syn":
        if port is None:
            yield {"type": "error", "value": "Port is required for ZMap TCP SYN scan."}
            return
        command.extend(["-p", str(port), target])
    elif scan_type == "icmp_echo":
        command.extend(["--probe-module=icmp_echoscan", target])
    else:
        yield {"type": "error", "value": "Unsupported ZMap scan type."}
        return

    command.extend(["--output-module=csv", "--output-fields=*"])
    logger.info("Starting ZMap scan for validated target %s", target)

    try:
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except (OSError, PermissionError):
        logger.exception("Failed to start ZMap")
        yield {"type": "error", "value": "Failed to start ZMap."}
        return

    yield {"type": "process", "value": proc}

    progress_queue = Queue()
    threading.Thread(
        target=enqueue_output,
        args=(proc.stderr, progress_queue),
        daemon=True,
    ).start()

    start_time = time.monotonic()
    timeout = 300

    try:
        while proc.poll() is None:
            if _cancel_requested(cancel_check):
                logger.info("ZMap scan canceled")
                _terminate_process(proc)
                yield {"type": "cancelled", "value": "Scan canceled."}
                return
            if time.monotonic() - start_time > timeout:
                logger.warning("ZMap scan timed out")
                _terminate_process(proc)
                yield {"type": "error", "value": "ZMap scan timed out after 5 minutes."}
                return

            try:
                line = progress_queue.get(timeout=0.1)
                if line is None:
                    continue
                if "%" in line:
                    match = re.search(r"(\d+(?:\.\d+)?)%\s+done", line)
                    if match:
                        yield {"type": "progress", "value": int(float(match.group(1)))}
            except Empty:
                continue

        stdout, stderr = proc.communicate()

        if proc.returncode != 0:
            logger.warning(
                "ZMap failed with return code %s: %s",
                proc.returncode,
                stderr[-1000:],
            )
            yield {"type": "error", "value": "ZMap scan failed."}
            return

        try:
            lines = [line for line in stdout.splitlines() if line.strip()]
            if len(lines) < 2:
                results = {"hosts": []}
            else:
                header = lines[0].split(",")
                if "saddr" in header:
                    ip_index = header.index("saddr")
                elif "daddr" in header:
                    ip_index = header.index("daddr")
                else:
                    raise ValueError("Address field missing from ZMap output")

                hosts = []
                for line in lines[1:]:
                    parts = line.split(",")
                    if ip_index >= len(parts):
                        continue
                    host_ip = parts[ip_index]
                    hosts.append(
                        {
                            "host": host_ip,
                            "ports": [{"portid": str(port), "state": "open"}],
                        }
                    )
                results = {"hosts": hosts}
        except Exception:
            logger.exception("Failed to parse ZMap output")
            yield {"type": "error", "value": "Failed to parse ZMap output."}
            return

        yield {"type": "result", "value": results}
    finally:
        if proc.poll() is None:
            _terminate_process(proc)


def _run_masscan_scan(target, scan_type="tcp_scan", port=None, cancel_check=None):
    if not is_valid_scan_target(target):
        yield {"type": "error", "value": "Invalid scan target."}
        return

    masscan_path, error = _require_executable("masscan")
    if error:
        yield {"type": "error", "value": error}
        return

    command = [masscan_path, target, "--rate", "1000"]
    if scan_type == "tcp_scan":
        if port is None:
            yield {"type": "error", "value": "Port is required for Masscan TCP scan."}
            return
        command.extend(["-p", str(port)])
    elif scan_type == "udp_scan":
        if port is None:
            yield {"type": "error", "value": "Port is required for Masscan UDP scan."}
            return
        command.extend([f"-pU:{port}"])
    elif scan_type == "ping_scan":
        command.append("--ping")
    else:
        yield {"type": "error", "value": "Unsupported Masscan scan type."}
        return

    logger.info("Starting Masscan scan for validated target %s", target)

    try:
        proc = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except (OSError, PermissionError):
        logger.exception("Failed to start Masscan")
        yield {"type": "error", "value": "Failed to start Masscan."}
        return

    yield {"type": "process", "value": proc}

    progress_queue = Queue()
    threading.Thread(
        target=enqueue_output,
        args=(proc.stderr, progress_queue),
        daemon=True,
    ).start()

    start_time = time.monotonic()
    timeout = 300

    try:
        while proc.poll() is None:
            if _cancel_requested(cancel_check):
                logger.info("Masscan scan canceled")
                _terminate_process(proc)
                yield {"type": "cancelled", "value": "Scan canceled."}
                return
            if time.monotonic() - start_time > timeout:
                logger.warning("Masscan scan timed out")
                _terminate_process(proc)
                yield {"type": "error", "value": "Masscan scan timed out after 5 minutes."}
                return

            try:
                line = progress_queue.get(timeout=0.1)
                if line is None:
                    continue
                match = re.search(r"(\d+(?:\.\d+)?)%\s+done", line)
                if match:
                    yield {"type": "progress", "value": int(float(match.group(1)))}
            except Empty:
                continue

        stdout, stderr = proc.communicate()

        if proc.returncode != 0 and "found=0" not in stderr:
            logger.warning(
                "Masscan failed with return code %s: %s",
                proc.returncode,
                stderr[-1000:],
            )
            yield {"type": "error", "value": "Masscan scan failed."}
            return

        try:
            found_hosts = {}
            for line in stdout.splitlines():
                port_match = re.search(
                    r"Discovered open port (\d+)/(\w+) on (\S+)",
                    line,
                )
                host_match = re.search(r"Host: (\S+)\s", line)

                if port_match:
                    port_id, _, host_ip = port_match.groups()
                    found_hosts.setdefault(host_ip, []).append(
                        {"portid": port_id, "state": "open"}
                    )
                elif host_match:
                    host_ip = host_match.group(1)
                    found_hosts.setdefault(host_ip, [])

            results = {
                "hosts": [
                    {"host": ip_address, "ports": ports}
                    for ip_address, ports in found_hosts.items()
                ]
            }
        except Exception:
            logger.exception("Failed to parse Masscan output")
            yield {"type": "error", "value": "Failed to parse Masscan output."}
            return

        yield {"type": "result", "value": results}
    finally:
        if proc.poll() is None:
            _terminate_process(proc)


def run_scan(tool, target, scan_type="default", port=None, cancel_check=None):
    if not is_valid_scan_target(target):
        raise ValueError("Invalid scan target")

    scanner_map = {
        "nmap": _run_nmap_scan,
        "zmap": _run_zmap_scan,
        "masscan": _run_masscan_scan,
    }
    scanner_func = scanner_map.get(tool)
    if scanner_func is None:
        raise ValueError("Unknown scanner tool")

    return scanner_func(
        target,
        scan_type,
        port=port,
        cancel_check=cancel_check,
    )
