import unittest
from unittest.mock import patch

from flask import Flask

from security_engine.base import SecurityEngineNotConfigured, SecurityEngineUpstreamError
import security_engine.routes as routes


class FakeEngine:
    def status(self):
        return {"provider": "wazuh", "manager_connected": True}

    def overview(self):
        return {"provider": "wazuh", "agents": {"total": 1}}

    def agents(self, limit=100):
        return [{"id": "001", "name": "agent", "limit": limit}]

    def alerts(self, limit=50):
        return [{"id": "alert-1", "level": 10, "limit": limit}]

    def sca(self, agent_id, limit=100):
        return [{"policy_id": "cis", "agent_id": agent_id, "limit": limit}]

    def fim(self, agent_id, limit=100):
        return [{"path": "/etc/hosts", "agent_id": agent_id, "limit": limit}]


class ErrorEngine(FakeEngine):
    def alerts(self, limit=50):
        raise SecurityEngineNotConfigured("indexer missing")

    def status(self):
        raise SecurityEngineUpstreamError("manager down", status_code=503)


class SecurityEngineRouteTests(unittest.TestCase):
    def _client(self, engine):
        app = Flask(__name__)
        with patch.object(routes, "clerk_authorized", side_effect=lambda view: view):
            app.register_blueprint(routes.create_security_blueprint(engine))
        return app.test_client()

    def test_not_configured_returns_controlled_503(self):
        response = self._client(None).get("/api/security/overview")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["code"], "security_engine_not_configured")

    def test_normalized_routes_return_provider_data(self):
        client = self._client(FakeEngine())
        self.assertEqual(client.get("/api/security/status").status_code, 200)
        self.assertEqual(client.get("/api/security/overview").status_code, 200)
        self.assertEqual(
            client.get("/api/security/agents?limit=20").get_json()[0]["limit"],
            20,
        )
        self.assertEqual(
            client.get("/api/security/alerts?limit=10").get_json()[0]["limit"],
            10,
        )
        self.assertEqual(
            client.get("/api/security/sca?agent_id=001&limit=25").get_json()[0]["agent_id"],
            "001",
        )
        self.assertEqual(
            client.get("/api/security/fim?agent_id=001&limit=25").get_json()[0]["agent_id"],
            "001",
        )

    def test_query_bounds_and_agent_ids_are_validated(self):
        client = self._client(FakeEngine())
        self.assertEqual(client.get("/api/security/alerts?limit=201").status_code, 400)
        self.assertEqual(client.get("/api/security/agents?limit=0").status_code, 400)
        self.assertEqual(client.get("/api/security/sca?agent_id=../1").status_code, 400)
        self.assertEqual(client.get("/api/security/fim?agent_id=abc").status_code, 400)

    def test_partial_configuration_and_upstream_failure_are_normalized(self):
        client = self._client(ErrorEngine())
        missing = client.get("/api/security/alerts")
        self.assertEqual(missing.status_code, 503)
        self.assertEqual(
            missing.get_json()["code"],
            "security_engine_capability_not_configured",
        )

        upstream = client.get("/api/security/status")
        self.assertEqual(upstream.status_code, 502)
        self.assertEqual(upstream.get_json()["code"], "security_engine_upstream_error")


if __name__ == "__main__":
    unittest.main()
