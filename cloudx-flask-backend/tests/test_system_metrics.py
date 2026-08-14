from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from security_engine.wazuh_metrics import WazuhSystemMetricsProvider
from system_metrics import _agentless_metrics, _local_network_throughput


class LocalSystemMetricsTests(TestCase):
    @patch("system_metrics.time.sleep", return_value=None)
    @patch("system_metrics.time.monotonic", side_effect=[10.0, 10.5])
    @patch(
        "system_metrics.psutil.net_io_counters",
        side_effect=[
            SimpleNamespace(bytes_recv=1_000_000, bytes_sent=2_000_000),
            SimpleNamespace(bytes_recv=2_048_576, bytes_sent=3_048_576),
        ],
    )
    def test_network_throughput_uses_real_counter_deltas(
        self, _net_counters, _monotonic, _sleep
    ):
        rx_mib, tx_mib = _local_network_throughput(sample_seconds=0.2)
        self.assertAlmostEqual(rx_mib, 2.0, places=5)
        self.assertAlmostEqual(tx_mib, 2.0, places=5)

    @patch("system_metrics.ping_host", return_value=17.25)
    def test_agentless_remote_target_only_reports_measured_latency(self, _ping):
        payload = _agentless_metrics("example.com")
        self.assertEqual(payload["source"], "agentless_ping")
        self.assertTrue(payload["is_agentless"])
        self.assertEqual(payload["cpu"], [])
        self.assertEqual(payload["memory"], [])
        self.assertEqual(payload["network"], [])
        self.assertAlmostEqual(payload["latency"][0]["value"], 17.25)
        self.assertFalse(payload["availability"]["cpu"])
        self.assertFalse(payload["availability"]["network_throughput"])
        self.assertTrue(payload["availability"]["latency"])


class _FakeServerClient:
    def __init__(self):
        self.calls = []

    def get(self, path, query=None):
        self.calls.append((path, query))
        if path.endswith("/hardware"):
            return {
                "data": {
                    "affected_items": [
                        {
                            "agent_id": "001",
                            "cpu": {"name": "Test CPU", "cores": 4, "mhz": 2500},
                            "ram": {"usage": 42, "total": 8192, "free": 4751},
                            "scan": {"time": "2026-08-14T12:00:00+00:00"},
                        }
                    ]
                }
            }
        if path.endswith("/netiface"):
            return {
                "data": {
                    "affected_items": [
                        {
                            "name": "eth0",
                            "rx": {"bytes": 1000},
                            "tx": {"bytes": 2000},
                            "scan": {"time": "2026-08-14T12:01:00+00:00"},
                        },
                        {
                            "name": "eth1",
                            "rx": {"bytes": 3000},
                            "tx": {"bytes": 4000},
                            "scan": {"time": "2026-08-14T12:01:00+00:00"},
                        },
                    ]
                }
            }
        raise AssertionError(f"Unexpected Wazuh path: {path}")


class _FakeEngine:
    def __init__(self):
        self.server_client = _FakeServerClient()

    def agents(self, limit=100):
        self.last_limit = limit
        return [
            {
                "id": "001",
                "name": "workstation-01",
                "ip": "192.0.2.10",
                "status": "active",
            }
        ]


class WazuhSystemMetricsProviderTests(TestCase):
    def test_matches_agent_and_returns_real_syscollector_snapshot(self):
        engine = _FakeEngine()
        provider = WazuhSystemMetricsProvider(engine)

        payload = provider.metrics_for_target("192.0.2.10")

        self.assertEqual(engine.last_limit, 500)
        self.assertEqual(payload["source"], "wazuh_syscollector")
        self.assertTrue(payload["is_agent_based"])
        self.assertFalse(payload["is_agentless"])
        self.assertEqual(payload["agent"]["id"], "001")
        self.assertEqual(payload["memory"][0]["value"], 42.0)
        self.assertEqual(payload["network_counters"]["rx_bytes"], 4000)
        self.assertEqual(payload["network_counters"]["tx_bytes"], 6000)
        self.assertEqual(payload["hardware"]["cpu_name"], "Test CPU")
        self.assertEqual(payload["cpu"], [])
        self.assertEqual(payload["network"], [])
        self.assertFalse(payload["availability"]["cpu"])
        self.assertFalse(payload["availability"]["network_throughput"])
        self.assertTrue(payload["availability"]["memory"])
        self.assertEqual(payload["collected_at"], "2026-08-14T12:01:00+00:00")

    def test_matches_agent_by_id_or_name_and_returns_none_for_unmanaged_target(self):
        provider = WazuhSystemMetricsProvider(_FakeEngine())
        self.assertIsNotNone(provider.metrics_for_target("001"))
        self.assertIsNotNone(provider.metrics_for_target("WORKSTATION-01"))
        self.assertIsNone(provider.metrics_for_target("unmanaged.example.com"))


if __name__ == "__main__":
    import unittest

    unittest.main()
