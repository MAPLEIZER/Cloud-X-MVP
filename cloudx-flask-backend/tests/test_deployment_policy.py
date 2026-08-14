import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

# app.py intentionally fails closed without production configuration. Supply
# inert test values before importing the application; no database connection is
# opened by these endpoint tests.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://cloudx:cloudx-test@127.0.0.1:5432/cloudx",
)
os.environ.setdefault("CLERK_SECRET_KEY", "sk_test_unit_only")
os.environ.setdefault("CLERK_AUTHORIZED_PARTIES", "http://localhost:5173")
os.environ.setdefault("CLERK_ALLOWED_USER_IDS", "user_ci")
os.environ.setdefault(
    "DEPLOYMENT_TARGET_ALLOWLIST_JSON",
    '{"user:user_ci":["10.20.30.0/24"],"org:org_ci":["192.0.2.50"]}',
)
os.environ.setdefault("ENABLE_WINDOWS_AGENT_DEPLOYMENT", "false")

import auth  # noqa: E402
from app import app, deployer  # noqa: E402


class DeploymentPolicyEndpointTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    @staticmethod
    def _auth_state(payload=None):
        return SimpleNamespace(
            is_signed_in=True,
            payload=payload or {"sub": "user_ci"},
        )

    @staticmethod
    def _payload(target, os_type="linux"):
        return {
            "target": target,
            "os_type": os_type,
            "username": "cloudx-admin",
            "password": "unit-test-password",
            "manager_ip": "10.20.30.2",
            "agent_name": "agent-01",
            "group": "default",
        }

    def test_allowed_user_target_reaches_deployer(self):
        with (
            patch.object(auth, "authenticate_request", return_value=self._auth_state()),
            patch.object(
                deployer,
                "deploy_linux",
                return_value={"status": "success", "output": "ok"},
            ) as deploy_linux,
        ):
            response = self.client.post(
                "/api/deploy/agent",
                json=self._payload("10.20.30.45"),
            )

        self.assertEqual(response.status_code, 200)
        deploy_linux.assert_called_once()

    def test_disallowed_target_is_blocked_before_remote_execution(self):
        with (
            patch.object(auth, "authenticate_request", return_value=self._auth_state()),
            patch.object(deployer, "deploy_linux") as deploy_linux,
        ):
            response = self.client.post(
                "/api/deploy/agent",
                json=self._payload("10.20.31.45"),
            )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            response.get_json()["error"],
            "Deployment target is not authorized",
        )
        deploy_linux.assert_not_called()

    def test_active_org_can_authorize_target(self):
        state = self._auth_state({"sub": "user_ci", "o": {"id": "org_ci"}})
        with (
            patch.object(auth, "authenticate_request", return_value=state),
            patch.object(
                deployer,
                "deploy_linux",
                return_value={"status": "success", "output": "ok"},
            ) as deploy_linux,
        ):
            response = self.client.post(
                "/api/deploy/agent",
                json=self._payload("192.0.2.50"),
            )

        self.assertEqual(response.status_code, 200)
        deploy_linux.assert_called_once()

    def test_legacy_org_id_claim_is_supported(self):
        self.assertEqual(auth._active_org_id({"org_id": "org_legacy"}), "org_legacy")
        self.assertEqual(auth._active_org_id({"o": {"id": "org_v2"}}), "org_v2")

    def test_windows_deployment_is_disabled_by_default(self):
        with (
            patch.object(auth, "authenticate_request", return_value=self._auth_state()),
            patch.object(deployer, "deploy_windows") as deploy_windows,
        ):
            response = self.client.post(
                "/api/deploy/agent",
                json=self._payload("10.20.30.45", os_type="windows"),
            )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()["error"], "Windows agent deployment is disabled")
        deploy_windows.assert_not_called()


if __name__ == "__main__":
    unittest.main()
