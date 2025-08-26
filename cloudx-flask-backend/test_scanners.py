#!/usr/bin/env python3

"""
Test script for scanner functionality with timeout
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'scanners'))

from scanners.network_scanners import run_scan

def test_nmap_scan():
    print("Testing Nmap scan with timeout...")
    try:
        # Test with a target that should respond quickly
        # Using scanme.nmap.org which is a test site provided by nmap
        for update in run_scan('nmap', 'scanme.nmap.org', 'quick'):
            print(f"Update: {update}")
            if update['type'] == 'result':
                print("Nmap scan completed successfully!")
                return True
            elif update['type'] == 'error':
                print(f"Nmap scan failed: {update['value']}")
                return False
    except Exception as e:
        print(f"Exception during Nmap scan: {e}")
        return False

def test_zmap_scan():
    print("Testing ZMap scan with timeout...")
    try:
        # Test with a target that should respond quickly
        for update in run_scan('zmap', '127.0.0.1', 'tcp_syn', port=80):
            print(f"Update: {update}")
            if update['type'] == 'result':
                print("ZMap scan completed successfully!")
                return True
            elif update['type'] == 'error':
                print(f"ZMap scan failed: {update['value']}")
                return False
    except Exception as e:
        print(f"Exception during ZMap scan: {e}")
        return False

def test_masscan_scan():
    print("Testing Masscan scan with timeout...")
    try:
        # Test with a target that should respond quickly
        for update in run_scan('masscan', '127.0.0.1', 'tcp_scan', port=80):
            print(f"Update: {update}")
            if update['type'] == 'result':
                print("Masscan scan completed successfully!")
                return True
            elif update['type'] == 'error':
                print(f"Masscan scan failed: {update['value']}")
                return False
    except Exception as e:
        print(f"Exception during Masscan scan: {e}")
        return False

if __name__ == "__main__":
    print("Running scanner tests with timeout functionality...")
    
    # Test Nmap
    success = test_nmap_scan()
    if not success:
        print("Nmap test failed")
    
    # Test ZMap (requires root, so might fail in test environment)
    # success = test_zmap_scan()
    # if not success:
    #     print("ZMap test failed")
    
    # Test Masscan (requires root, so might fail in test environment)
    # success = test_masscan_scan()
    # if not success:
    #     print("Masscan test failed")
    
    print("Scanner tests completed.")
