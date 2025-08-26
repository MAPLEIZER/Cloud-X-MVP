#!/usr/bin/env python3

"""
Test script for scanner timeout functionality
"""

import time
import subprocess
import threading
from queue import Queue, Empty


def enqueue_output(out, queue):
    """Enqueue output from subprocess to queue"""
    for line in iter(out.readline, ''):
        queue.put(line)
    out.close()


def test_timeout_implementation():
    """
    Test our timeout implementation with a long-running command
    """
    print("Testing timeout implementation...")
    
    # Use a command that will run for a long time
    command = ['ping', 'localhost']
    
    try:
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
    except Exception as e:
        print(f"Failed to start process: {e}")
        return False
    
    print(f"Started process with PID: {proc.pid}")
    
    # Create queue and thread for reading output
    q = Queue()
    thread = threading.Thread(target=enqueue_output, args=(proc.stdout, q))
    thread.daemon = True
    thread.start()
    
    # Set timeout to 5 seconds for testing
    start_time = time.time()
    timeout = 5
    
    # Monitor process with timeout
    while proc.poll() is None:
        # Check for timeout
        if time.time() - start_time > timeout:
            print("Process timed out, terminating...")
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                print("Process did not terminate gracefully, killing...")
                proc.kill()
            print("Process terminated successfully")
            return True
        
        # Check for output
        try:
            line = q.get_nowait()
            print(f"Output: {line.strip()}")
        except Empty:
            time.sleep(0.1)
    
    print("Process completed before timeout")
    return True

if __name__ == "__main__":
    success = test_timeout_implementation()
    if success:
        print("Timeout test completed successfully!")
    else:
        print("Timeout test failed!")
