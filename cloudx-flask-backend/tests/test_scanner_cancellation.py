import io
import unittest
from unittest.mock import patch

from scanners import network_scanners


class FakeProcess:
    def __init__(self):
        self.returncode = None
        self.stdout = io.StringIO("")
        self.stderr = io.StringIO("")
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = -15

    def wait(self, timeout=None):
        del timeout
        return self.returncode

    def kill(self):
        self.killed = True
        self.returncode = -9

    def communicate(self):
        return "", ""


class ScannerCancellationTests(unittest.TestCase):
    def _assert_scanner_cancels(self, scanner, scan_type, port=None):
        process = FakeProcess()
        with (
            patch.object(
                network_scanners,
                "_require_executable",
                return_value=("/usr/bin/scanner", None),
            ),
            patch.object(network_scanners.subprocess, "Popen", return_value=process),
        ):
            updates = list(
                scanner(
                    "127.0.0.1",
                    scan_type,
                    port=port,
                    cancel_check=lambda: True,
                )
            )

        self.assertEqual(updates[0]["type"], "process")
        self.assertEqual(updates[1]["type"], "cancelled")
        self.assertTrue(process.terminated)

    def test_nmap_cancellation_terminates_subprocess(self):
        self._assert_scanner_cancels(
            network_scanners._run_nmap_scan,
            "default",
        )

    def test_zmap_cancellation_terminates_subprocess(self):
        self._assert_scanner_cancels(
            network_scanners._run_zmap_scan,
            "tcp_syn",
            port=443,
        )

    def test_masscan_cancellation_terminates_subprocess(self):
        self._assert_scanner_cancels(
            network_scanners._run_masscan_scan,
            "tcp_scan",
            port=443,
        )


if __name__ == "__main__":
    unittest.main()
