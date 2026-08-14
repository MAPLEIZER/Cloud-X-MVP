import os
import unittest
from unittest.mock import patch

from security_engine.base import SecurityEngineNotConfigured, SecurityEngineUpstreamError
from security_engine.wazuh import (
    WazuhSecurityEngine,
    _WazuhServerClient,
)


class FakeHttp:
    def __init__(self):
        self.calls = []
        self.auth_count = 0
        self.get_count = 0

    def request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        if path == "/security/user/authenticate":
            self.auth_count += 1
            return f"token-{self.auth_count}"
        if path == "/agents":
            self.get_count += 1
            if self.get_count == 1:
                raise SecurityEngineUpstreamError("expired", status_code=401)
            return {"data": {"affected_items": [{"id": "001", "name": "agent"}]}}
        raise AssertionError(f"Unexpected request: {method} {path}")


class FakeServerClient:
    def __init__(self):
        self.calls = []

    def get(self, path, query=None):
        self.calls.append((path, query))
        if path == "/":
            return {
                "data": {
                    "api_version": "4.14.1",
                    "hostname": "wazuh-manager",
                }
            }
        if path == "/agents":
            return {
                "data": {
                    "affected_items": [
                        {
                            "id": "001",
                            "name": "workstation-01",
                            "ip": "10.0.0.10",
                            "status": "active",
                            "group": "default,windows",
                            "version": "Wazuh v4.14.1",
                            "node_name": "node-1",
                            "lastKeepAlive": "2026-08-14T11:00:00Z",
                            "os": {
                                "name": "Windows 11",
                                "version": "24H2",
                                "platform": "windows",
                                "arch": "x86_64",
                            },
                        },
                        {
                            "id": "002",
                            "name": "server-02",
                            "status": "disconnected",
                            "os": {"name": "Ubuntu"},
                        },
                    ]
                }
            }
        if path == "/sca/001":
            return {
                "data": {
                    "affected_items": [
                        {
                            "policy_id": "cis_win11",
                            "name": "CIS Windows 11",
                            "pass": 90,
                            "fail": 10,
                            "invalid": 0,
                            "total_checks": 100,
                            "score": 90,
                            "end_scan": "2026-08-14T10:50:00Z",
                        }
                    ]
                }
            }
        if path == "/syscheck/001":
            return {
                "data": {
                    "affected_items": [
                        {
                            "file": "/etc/ssh/sshd_config",
                            "type": "file",
                            "size": 4096,
                            "perm": "rw-r--r--",
                            "uname": "root",
                            "gname": "root",
                            "sha256": "abc123",
                            "changes": 2,
                            "mtime": "2026-08-14T10:40:00Z",
                            "date": "2026-08-14T10:45:00Z",
                        }
                    ]
                }
            }
        raise AssertionError(f"Unexpected server path: {path}")


class FakeIndexerClient:
    def __init__(self):
        self.search_calls = 0

    def search_alerts(self, limit):
        self.search_calls += 1
        return {
            "hits": {
                "hits": [
                    {
                        "_id": "alert-1",
                        "_source": {
                            "timestamp": "2026-08-14T11:05:00Z",
                            "rule": {
                                "id": "5710",
                                "level": 12,
                                "description": "Multiple authentication failures",
                                "groups": ["authentication_failed"],
                                "mitre": {"id": ["T1110"]},
                            },
                            "agent": {
                                "id": "001",
                                "name": "workstation-01",
                                "ip": "10.0.0.10",
                            },
                            "manager": {"name": "wazuh-manager"},
                            "location": "sshd",
                        },
                    }
                ]
            }
        }

    def health(self):
        return {"status": "green"}


class WazuhEngineTests(unittest.TestCase):
    def test_server_client_refreshes_jwt_once_after_401(self):
        http = FakeHttp()
        client = _WazuhServerClient(http, "api-user", "api-password")

        result = client.get("/agents", query={"limit": 1})

        self.assertEqual(result["data"]["affected_items"][0]["id"], "001")
        self.assertEqual(http.auth_count, 2)
        bearer_headers = [
            call[2].get("headers", {}).get("Authorization")
            for call in http.calls
            if call[1] == "/agents"
        ]
        self.assertEqual(bearer_headers, ["Bearer token-1", "Bearer token-2"])

    def test_normalizes_agents_alerts_sca_and_fim(self):
        server = FakeServerClient()
        indexer = FakeIndexerClient()
        engine = WazuhSecurityEngine(server, indexer, cache_ttl_seconds=60)

        agents = engine.agents()
        self.assertEqual(agents[0]["groups"], ["default", "windows"])
        self.assertEqual(agents[0]["os"]["platform"], "windows")
        self.assertEqual(agents[1]["status"], "disconnected")

        alerts = engine.alerts()
        self.assertEqual(alerts[0]["level"], 12)
        self.assertEqual(alerts[0]["mitre_ids"], ["T1110"])
        self.assertEqual(alerts[0]["agent"]["id"], "001")

        sca = engine.sca("001")
        self.assertEqual(sca[0]["failed"], 10)
        self.assertEqual(sca[0]["score"], 90.0)

        fim = engine.fim("001")
        self.assertEqual(fim[0]["path"], "/etc/ssh/sshd_config")
        self.assertEqual(fim[0]["changes"], 2)

    def test_overview_is_normalized_and_cached(self):
        server = FakeServerClient()
        indexer = FakeIndexerClient()
        engine = WazuhSecurityEngine(server, indexer, cache_ttl_seconds=60)

        first = engine.overview()
        second = engine.overview()

        self.assertEqual(first, second)
        self.assertEqual(first["agents"], {"total": 2, "active": 1, "disconnected": 1})
        self.assertEqual(first["alerts"]["critical"], 1)
        self.assertEqual(indexer.search_calls, 1)

    def test_status_reports_manager_and_indexer_health(self):
        engine = WazuhSecurityEngine(
            FakeServerClient(), FakeIndexerClient(), cache_ttl_seconds=60
        )
        status = engine.status()
        self.assertEqual(status["manager_version"], "4.14.1")
        self.assertEqual(status["indexer_status"], "green")
        self.assertTrue(status["indexer_configured"])

    def test_alerts_fail_closed_when_indexer_is_not_configured(self):
        engine = WazuhSecurityEngine(FakeServerClient(), None)
        with self.assertRaises(SecurityEngineNotConfigured):
            engine.alerts()
        overview = engine.overview()
        self.assertFalse(overview["alerts"]["available"])

    def test_from_env_is_optional_but_partial_config_fails_startup(self):
        names = [
            "WAZUH_API_URL",
            "WAZUH_API_USERNAME",
            "WAZUH_API_PASSWORD",
            "WAZUH_INDEXER_URL",
            "WAZUH_INDEXER_USERNAME",
            "WAZUH_INDEXER_PASSWORD",
        ]
        clean = {name: "" for name in names}
        with patch.dict(os.environ, clean, clear=False):
            self.assertIsNone(WazuhSecurityEngine.from_env())

        with patch.dict(
            os.environ,
            {
                **clean,
                "WAZUH_API_URL": "https://manager.example.com:55000",
                "WAZUH_API_USERNAME": "api-user",
            },
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                WazuhSecurityEngine.from_env()

    def test_api_urls_must_use_https(self):
        with patch.dict(
            os.environ,
            {
                "WAZUH_API_URL": "http://manager.example.com:55000",
                "WAZUH_API_USERNAME": "api-user",
                "WAZUH_API_PASSWORD": "password",
            },
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                WazuhSecurityEngine.from_env()


if __name__ == "__main__":
    unittest.main()
