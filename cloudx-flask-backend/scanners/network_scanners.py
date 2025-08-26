import subprocess
import re
import json
import xmltodict
import threading
import time
import shutil
import os
import logging
import signal
from queue import Queue, Empty

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def enqueue_output(out, queue):
    """Helper function to enqueue output from a pipe"""
    try:
        with out:
            for line in iter(out.readline, ''):
                queue.put(line)
    finally:
        queue.put(None)

def _run_nmap_scan(target, scan_type='default', port=None):
    """
    Runs an Nmap scan on the given target with a specified scan type,
    yielding progress updates and returning the final JSON result.
    """
    logger.debug(f"Starting Nmap scan: target={target}, scan_type={scan_type}, port={port}")
    scan_args = {
        'default': '-T4 -F',
        'quick': '-T4 -F',
        'intense': '-T4 -A -v',
        'tcp': '-p 1-65535',
        'udp': '-sU -T4',
    }

    arguments = scan_args.get(scan_type, scan_args['default'])
    
    # Check if nmap is installed
    nmap_path = shutil.which('nmap')
    if not nmap_path:
        logger.error('nmap is not installed or not in PATH')
        yield {'type': 'error', 'value': 'nmap is not installed or not in PATH. Please install it with: sudo apt install nmap'}
        return
    
    # Check if we have execute permissions
    if not os.access(nmap_path, os.X_OK):
        logger.error(f'nmap is not executable at path: {nmap_path}')
        yield {'type': 'error', 'value': f'nmap is not executable. Please check permissions for {nmap_path}'}
        return
    
    command = f'nmap {arguments} -v -oX - {target}'

    logger.debug(f"Executing Nmap command: {command}")

    try:
        proc = subprocess.Popen(
            command.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding='utf-8',
            errors='ignore' # Ignore characters that can't be decoded
        )
    except PermissionError:
        logger.error('Permission denied when trying to run nmap')
        yield {'type': 'error', 'value': 'Permission denied when trying to run nmap. Please check permissions.'}
        return
    except Exception as e:
        logger.error(f'Failed to start nmap: {str(e)}')
        yield {'type': 'error', 'value': f'Failed to start nmap: {str(e)}'}
        return

    yield {'type': 'process', 'value': proc}

    q = Queue()

    def reader_thread(pipe, queue):
        try:
            with pipe:
                for line in iter(pipe.readline, ''):
                    queue.put(line)
        finally:
            queue.put(None)

    threading.Thread(target=reader_thread, args=[proc.stderr, q], daemon=True).start()

    # Timeout after 5 minutes
    start_time = time.time()
    timeout = 300

    while proc.poll() is None:
        # Check for timeout
        if time.time() - start_time > timeout:
            logger.warning("Nmap scan timed out after 5 minutes")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            yield {'type': 'error', 'value': 'Nmap scan timed out after 5 minutes'}
            return

        try:
            line = q.get(timeout=0.1)
            if line is None:
                break
            match = re.search(r'About (\d+\.\d+)% done', line)
            if match:
                progress = int(float(match.group(1)))
                yield {'type': 'progress', 'value': progress}
            logger.debug(f"Nmap output: {line.strip()}")
        except Empty:
            continue

    stdout_data, stderr_data = proc.communicate()

    if proc.returncode != 0:
        logger.error(f"Nmap scan failed with return code {proc.returncode}. Stderr: {stderr_data}")
        yield {'type': 'error', 'value': f'Nmap scan failed: {stderr_data}'}
        return
    
    logger.debug("Nmap scan completed successfully")

    if not stdout_data.strip():
        yield {'type': 'error', 'value': 'Nmap returned no XML output.'}
        return

    try:
        json_output = xmltodict.parse(stdout_data)
        yield {'type': 'result', 'value': json_output}
    except Exception as e:
        logger.error(f'Failed to parse nmap XML output: {str(e)}')
        yield {'type': 'error', 'value': f'Failed to parse nmap XML output: {str(e)}'}

def _run_zmap_scan(target, scan_type='tcp_syn', port=None):
    """
    Runs a ZMap scan on the given target and port, yielding progress and results.
    """
    logger.debug(f"Starting ZMap scan: target={target}, scan_type={scan_type}, port={port}")
    # Check if zmap is installed
    zmap_path = shutil.which('zmap')
    if not zmap_path:
        logger.error('zmap is not installed or not in PATH')
        yield {'type': 'error', 'value': 'zmap is not installed or not in PATH. Please install it with: sudo apt install zmap'}
        return
    
    # Check if we have execute permissions
    if not os.access(zmap_path, os.X_OK):
        logger.error(f'zmap is not executable at path: {zmap_path}')
        yield {'type': 'error', 'value': f'zmap is not executable. Please check permissions for {zmap_path}'}
        return
    
    # ZMap typically requires root privileges for raw socket access
    # We'll proceed with the scan and handle permission errors in the subprocess call
    
    command = ['zmap']
    if scan_type == 'tcp_syn':
        if not port:
            logger.error('Port is required for ZMap TCP SYN scan')
            yield {'type': 'error', 'value': 'Port is required for ZMap TCP SYN scan'}
            return
        command.extend(['-p', str(port), target])
    elif scan_type == 'icmp_echo':
        command.extend(['--probe-module=icmp_echoscan', target])
    else:
        logger.error(f'Unsupported ZMap scan type: {scan_type}')
        yield {'type': 'error', 'value': f'Unsupported ZMap scan type: {scan_type}'}
        return

    command.extend(['--output-module=csv', '--output-fields=*'])

    logger.debug(f"Executing ZMap command: {' '.join(command)}")

    try:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    except PermissionError:
        logger.error('Permission denied when trying to run zmap')
        yield {'type': 'error', 'value': 'Permission denied when trying to run zmap. ZMap requires root privileges to access raw sockets. Please run the Cloud-X backend with sudo.'}
        return
    except Exception as e:
        logger.error(f'Failed to start zmap: {str(e)}')
        yield {'type': 'error', 'value': f'Failed to start zmap: {str(e)}'}
        return

    yield {'type': 'process', 'value': proc}

    q = Queue()
    thread = threading.Thread(target=enqueue_output, args=(proc.stderr, q))
    thread.daemon = True
    thread.start()

    # Timeout after 5 minutes
    start_time = time.time()
    timeout = 300

    while proc.poll() is None:
        # Check for timeout
        if time.time() - start_time > timeout:
            logger.warning("ZMap scan timed out after 5 minutes")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            yield {'type': 'error', 'value': 'ZMap scan timed out after 5 minutes'}
            return

        try:
            line = q.get_nowait()
            if '%' in line:
                try:
                    progress = float(line.split('%')[0].strip().split(' ')[-1])
                    yield {'type': 'progress', 'value': int(progress)}
                except (ValueError, IndexError):
                    pass # Ignore lines that don't contain valid progress
            logger.debug(f"ZMap output: {line.strip()}")
        except Empty:
            time.sleep(0.1)

    stdout, stderr = proc.communicate()

    if proc.returncode != 0:
        logger.error(f"ZMap scan failed with return code {proc.returncode}. Stderr: {stderr}")
        yield {'type': 'error', 'value': f'ZMap scan failed: {stderr}'}
        return

    logger.debug("ZMap scan completed successfully")

    try:
        # ZMap CSV output is just a list of IPs, one per line
        # We need to structure it to be somewhat consistent with Nmap's output
        lines = stdout.strip().split('\n')
        # The first line is the header, the last is a summary we can ignore
        if len(lines) < 2:
            results = {'hosts': []}
        else:
            # The header is something like 'saddr,daddr,sport,dport,ipid,ttl,seq,ack,in_window,unreach_code,unreach_reason,validation_passed'
            # We are primarily interested in the discovered IPs ('saddr' or 'daddr')
            header = lines[0].split(',')
            ip_index = -1
            if 'saddr' in header:
                ip_index = header.index('saddr')
            elif 'daddr' in header:
                ip_index = header.index('daddr')

            if ip_index == -1:
                raise ValueError("Could not find source or destination address in ZMap output")

            hosts = []
            for line in lines[1:]:
                if not line.strip():
                    continue
                parts = line.split(',')
                host_ip = parts[ip_index]
                hosts.append({
                    'host': host_ip,
                    'ports': [{'portid': str(port), 'state': 'open'}]
                })
            results = {'hosts': hosts}

        yield {'type': 'result', 'value': results}
    except Exception as e:
        logger.error(f'Failed to parse ZMap output: {str(e)}')
        yield {'type': 'error', 'value': f'Failed to parse ZMap output: {str(e)}'}

def _run_masscan_scan(target, scan_type='tcp_scan', port=None):
    """
    Runs a Masscan scan on the given target and port, yielding progress and results.
    """
    logger.debug(f"Starting Masscan scan: target={target}, scan_type={scan_type}, port={port}")
    # Check if masscan is installed
    masscan_path = shutil.which('masscan')
    if not masscan_path:
        logger.error('masscan is not installed or not in PATH')
        yield {'type': 'error', 'value': 'masscan is not installed or not in PATH. Please install it with: sudo apt install masscan'}
        return
    
    # Check if we have execute permissions
    if not os.access(masscan_path, os.X_OK):
        logger.error(f'masscan is not executable at path: {masscan_path}')
        yield {'type': 'error', 'value': f'masscan is not executable. Please check permissions for {masscan_path}'}
        return
    
    # Masscan typically requires root privileges for raw socket access
    # We'll proceed with the scan and handle permission errors in the subprocess call
    
    command = ['masscan', target, '--rate', '1000']
    if scan_type == 'tcp_scan':
        if not port:
            logger.error('Port is required for Masscan TCP scan')
            yield {'type': 'error', 'value': 'Port is required for Masscan TCP scan'}
            return
        command.extend(['-p', str(port)])
    elif scan_type == 'udp_scan':
        if not port:
            logger.error('Port is required for Masscan UDP scan')
            yield {'type': 'error', 'value': 'Port is required for Masscan UDP scan'}
            return
        command.extend(['-pU:' + str(port)])
    elif scan_type == 'ping_scan':
        command.append('--ping')
    else:
        logger.error(f'Unsupported Masscan scan type: {scan_type}')
        yield {'type': 'error', 'value': f'Unsupported Masscan scan type: {scan_type}'}
        return

    logger.debug(f"Executing Masscan command: {' '.join(command)}")

    try:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    except PermissionError:
        logger.error('Permission denied when trying to run masscan')
        yield {'type': 'error', 'value': 'Permission denied when trying to run masscan. Masscan requires root privileges to access raw sockets. Please run the Cloud-X backend with sudo.'}
        return
    except Exception as e:
        logger.error(f'Failed to start masscan: {str(e)}')
        yield {'type': 'error', 'value': f'Failed to start masscan: {str(e)}'}
        return

    yield {'type': 'process', 'value': proc}

    q = Queue()
    thread = threading.Thread(target=enqueue_output, args=(proc.stderr, q))
    thread.daemon = True
    thread.start()

    # Timeout after 5 minutes
    start_time = time.time()
    timeout = 300

    while proc.poll() is None:
        # Check for timeout
        if time.time() - start_time > timeout:
            logger.warning("Masscan scan timed out after 5 minutes")
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            yield {'type': 'error', 'value': 'Masscan scan timed out after 5 minutes'}
            return

        try:
            line = q.get_nowait()
            if 'rate:' in line and '%' in line:
                try:
                    # Example line: rate: 1130.52-kpps, 100.00% done, 0:00:00 remaining, found=0
                    progress_str = line.split(',')[1].strip().split('%')[0]
                    progress = float(progress_str)
                    yield {'type': 'progress', 'value': int(progress)}
                except (ValueError, IndexError):
                    pass # Ignore malformed progress lines
            logger.debug(f"Masscan output: {line.strip()}")
        except Empty:
            time.sleep(0.1)

    stdout, stderr = proc.communicate()

    if proc.returncode != 0 and 'found=0' not in stderr:
        # Masscan may exit with a non-zero code if no ports are found, which is not a true error.
        yield {'type': 'error', 'value': stderr or stdout}
        return

    try:
        # Parse Masscan's default output format
        # Example: Discovered open port 80/tcp on 192.168.1.1
        import re
        found_hosts = {}
        for line in stdout.strip().split('\n'):
            # Handle both port discovery and host discovery (from ping scans)
            port_match = re.search(r'Discovered open port (\d+)/(\w+) on (\S+)', line)
            host_match = re.search(r'Host: (\S+)\s', line) # For ping scan results

            if port_match:
                port_id, _, host_ip = port_match.groups()
                if host_ip not in found_hosts:
                    found_hosts[host_ip] = []
                found_hosts[host_ip].append({'portid': port_id, 'state': 'open'})
            elif host_match:
                host_ip = host_match.groups()[0]
                if host_ip not in found_hosts:
                    found_hosts[host_ip] = [] # No ports, just host discovery


        
        hosts_list = [{'host': ip, 'ports': ports} for ip, ports in found_hosts.items()]
        results = {'hosts': hosts_list}

        yield {'type': 'result', 'value': results}
    except Exception as e:
        yield {'type': 'error', 'value': f'Failed to parse Masscan output: {str(e)}'}

def run_scan(tool, target, scan_type='default', port=None):
    scanners = {
        'nmap': _run_nmap_scan,
        'zmap': _run_zmap_scan,
        'masscan': _run_masscan_scan
    }

    scanner_func = scanners.get(tool)

    if not scanner_func:
        raise ValueError(f"Unknown scanner tool: {tool}")

    return scanner_func(target, scan_type, port=port)
