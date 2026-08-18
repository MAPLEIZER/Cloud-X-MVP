import os
import unittest
from unittest.mock import patch

from flask import Flask

import error_tracking


class ErrorTrackingTests(unittest.TestCase):
    def setUp(self):
        self._initialised = error_tracking._INITIALIZED
        self._enabled = error_tracking._ENABLED
        error_tracking._INITIALIZED = False
        error_tracking._ENABLED = False

    def tearDown(self):
        error_tracking._INITIALIZED = self._initialised
        error_tracking._ENABLED = self._enabled

    def test_scrub_event_removes_request_secrets_query_and_frame_vars(self):
        event = {
            "request": {
                "url": "https://cloudx.example/api/scans?token=do-not-leak",
                "headers": {"Authorization": "Bearer do-not-leak"},
                "cookies": {"session": "do-not-leak"},
                "data": {"password": "do-not-leak"},
                "query_string": "token=do-not-leak",
            },
            "message": "password=do-not-leak",
            "exception": {
                "values": [
                    {
                        "value": "Bearer do-not-leak",
                        "stacktrace": {
                            "frames": [
                                {
                                    "filename": "app.py",
                                    "vars": {"secret": "do-not-leak"},
                                }
                            ]
                        },
                    }
                ]
            },
            "user": {
                "id": "user_123",
                "email": "operator@example.com",
                "ip_address": "203.0.113.10",
            },
        }

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ERROR_TRACKING_INCLUDE_USER_ID", None)
            cleaned = error_tracking.scrub_event(event)

        request_data = cleaned["request"]
        self.assertEqual(request_data["url"], "https://cloudx.example/api/scans")
        self.assertNotIn("headers", request_data)
        self.assertNotIn("cookies", request_data)
        self.assertNotIn("data", request_data)
        self.assertNotIn("query_string", request_data)
        self.assertNotIn("do-not-leak", str(cleaned))
        frame = cleaned["exception"]["values"][0]["stacktrace"]["frames"][0]
        self.assertNotIn("vars", frame)
        self.assertEqual(cleaned["user"], {})

    def test_error_tracking_is_disabled_without_dsn(self):
        with patch.dict(os.environ, {"ERROR_TRACKING_DSN": ""}, clear=False):
            with patch.object(error_tracking.sentry_sdk, "init") as init:
                self.assertFalse(error_tracking.init_error_tracking(component="api", flask=True))
                init.assert_not_called()
        self.assertFalse(error_tracking.is_error_tracking_enabled())

    def test_error_tracking_uses_privacy_first_sdk_options(self):
        env = {
            "ERROR_TRACKING_DSN": "https://public-key@glitchtip.internal/1",
            "ERROR_TRACKING_ENVIRONMENT": "staging",
            "ERROR_TRACKING_TRACES_SAMPLE_RATE": "0.01",
        }
        with patch.dict(os.environ, env, clear=False):
            with patch.object(error_tracking.sentry_sdk, "init") as init:
                with patch.object(error_tracking.sentry_sdk, "set_tag") as set_tag:
                    self.assertTrue(
                        error_tracking.init_error_tracking(component="api", flask=True)
                    )

        kwargs = init.call_args.kwargs
        self.assertEqual(kwargs["dsn"], env["ERROR_TRACKING_DSN"])
        self.assertEqual(kwargs["environment"], "staging")
        self.assertEqual(kwargs["traces_sample_rate"], 0.01)
        self.assertFalse(kwargs["send_default_pii"])
        self.assertEqual(kwargs["max_request_body_size"], "never")
        self.assertFalse(kwargs["auto_session_tracking"])
        self.assertIs(kwargs["before_send"], error_tracking.scrub_event)
        self.assertEqual(len(kwargs["integrations"]), 1)
        set_tag.assert_called_once_with("cloudx_component", "api")

    def test_invalid_dsn_is_rejected(self):
        with patch.dict(
            os.environ,
            {"ERROR_TRACKING_DSN": "file:///tmp/not-a-dsn"},
            clear=False,
        ):
            with self.assertRaises(RuntimeError):
                error_tracking.init_error_tracking(component="api")

    def test_authenticated_frontend_bridge_sanitizes_payload(self):
        app = Flask(__name__)
        app.register_blueprint(
            error_tracking.create_error_tracking_blueprint(lambda view: view)
        )
        client = app.test_client()

        with patch.object(error_tracking.sentry_sdk, "capture_event") as capture:
            response = client.post(
                "/api/client-errors",
                json={
                    "name": "TypeError",
                    "message": "password=do-not-leak",
                    "stack": "Bearer do-not-leak\nhttps://app.example/page?token=do-not-leak",
                    "source": "window.error",
                    "path": "/dashboard?token=do-not-leak",
                    "line": 42,
                    "column": 9,
                    "arbitrary": {"secret": "must-not-forward"},
                },
            )

        self.assertEqual(response.status_code, 202)
        event = capture.call_args.args[0]
        self.assertEqual(event["tags"]["cloudx_source"], "frontend")
        self.assertEqual(event["extra"]["frontend_path"], "/dashboard")
        self.assertEqual(event["extra"]["line"], 42)
        self.assertNotIn("do-not-leak", str(event))
        self.assertNotIn("arbitrary", str(event))

    def test_frontend_bridge_requires_message(self):
        app = Flask(__name__)
        app.register_blueprint(
            error_tracking.create_error_tracking_blueprint(lambda view: view)
        )
        response = app.test_client().post(
            "/api/client-errors", json={"source": "window.error"}
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
