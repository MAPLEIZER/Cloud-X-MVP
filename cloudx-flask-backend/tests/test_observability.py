import json
import logging
import unittest

from flask import Flask, jsonify

from observability import (
    CloudXJsonFormatter,
    create_health_blueprint,
    install_request_observability,
    redact_log_text,
)


class _FakeSession:
    def __init__(self, fail=False):
        self.fail = fail
        self.rolled_back = False

    def execute(self, statement):
        if self.fail:
            raise RuntimeError("postgresql://cloudx:do-not-leak@db/cloudx")
        return statement

    def rollback(self):
        self.rolled_back = True


class _FakeDB:
    def __init__(self, fail=False):
        self.session = _FakeSession(fail=fail)


class _HealthyEngine:
    def status(self):
        return {
            "manager_connected": True,
            "indexer_configured": True,
            "indexer_connected": True,
        }


class _DegradedEngine:
    def status(self):
        return {
            "manager_connected": False,
            "indexer_configured": True,
            "indexer_connected": False,
        }


class _ExplodingEngine:
    def status(self):
        raise RuntimeError("password=super-secret-wazuh-password")


class _CaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class ObservabilityTests(unittest.TestCase):
    def _health_client(self, db=None, queue_probe=None, engine=None):
        app = Flask(__name__)
        app.register_blueprint(
            create_health_blueprint(
                db or _FakeDB(),
                queue_probe or (lambda: None),
                security_engine=engine,
            )
        )
        return app.test_client()

    def test_liveness_does_not_depend_on_external_services(self):
        client = self._health_client(
            db=_FakeDB(fail=True),
            queue_probe=lambda: (_ for _ in ()).throw(RuntimeError("redis down")),
        )
        response = client.get("/api/health/live")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ok")

    def test_readiness_requires_postgres_and_redis(self):
        db = _FakeDB(fail=True)

        def queue_failure():
            raise RuntimeError("redis://user:do-not-leak@redis:6379/0")

        response = self._health_client(db=db, queue_probe=queue_failure).get(
            "/api/health/ready"
        )
        payload = response.get_json()
        self.assertEqual(response.status_code, 503)
        self.assertFalse(payload["ready"])
        self.assertEqual(payload["status"], "not_ready")
        self.assertEqual(payload["components"]["postgres"]["status"], "unavailable")
        self.assertEqual(
            payload["components"]["redis_queue"]["status"], "unavailable"
        )
        self.assertTrue(db.session.rolled_back)
        self.assertNotIn("do-not-leak", response.get_data(as_text=True))

    def test_unconfigured_wazuh_does_not_block_core_readiness(self):
        response = self._health_client().get("/api/health/ready")
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["ready"])
        self.assertEqual(
            payload["components"]["security_engine"]["status"], "not_configured"
        )

    def test_configured_wazuh_outage_is_reported_as_degraded_without_secret_leak(self):
        response = self._health_client(engine=_ExplodingEngine()).get(
            "/api/health/ready"
        )
        payload = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload["ready"])
        self.assertEqual(payload["status"], "degraded")
        self.assertEqual(
            payload["components"]["security_engine"]["status"], "unavailable"
        )
        self.assertNotIn("super-secret", response.get_data(as_text=True))

    def test_healthy_configured_wazuh_reports_ready(self):
        response = self._health_client(engine=_HealthyEngine()).get(
            "/api/health/ready"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ready")

    def test_disconnected_wazuh_reports_degraded(self):
        response = self._health_client(engine=_DegradedEngine()).get(
            "/api/health/ready"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "degraded")

    def test_request_id_is_propagated_without_logging_query_or_auth_header(self):
        app = Flask(__name__)
        install_request_observability(app)

        @app.get("/example")
        def example():
            return jsonify({"ok": True})

        logger = logging.getLogger("cloudx.request")
        handler = _CaptureHandler()
        previous_level = logger.level
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        try:
            response = app.test_client().get(
                "/example?token=do-not-log",
                headers={
                    "Authorization": "Bearer do-not-log",
                    "X-Request-ID": "trace-123",
                },
            )
        finally:
            logger.removeHandler(handler)
            logger.setLevel(previous_level)

        self.assertEqual(response.headers["X-Request-ID"], "trace-123")
        completion = next(
            record for record in handler.records if record.getMessage() == "request_complete"
        )
        self.assertEqual(completion.request_id, "trace-123")
        self.assertEqual(completion.path, "/example")
        self.assertEqual(completion.method, "GET")
        self.assertEqual(completion.status_code, 200)
        self.assertNotIn("do-not-log", completion.getMessage())
        self.assertFalse(hasattr(completion, "query_string"))
        self.assertFalse(hasattr(completion, "authorization"))

    def test_invalid_client_request_id_is_replaced(self):
        app = Flask(__name__)
        install_request_observability(app)

        @app.get("/example")
        def example():
            return "ok"

        response = app.test_client().get(
            "/example", headers={"X-Request-ID": "bad request id with spaces"}
        )
        request_id = response.headers["X-Request-ID"]
        self.assertNotEqual(request_id, "bad request id with spaces")
        self.assertGreater(len(request_id), 20)

    def test_json_formatter_redacts_common_secret_shapes(self):
        record = logging.LogRecord(
            "cloudx.test",
            logging.ERROR,
            __file__,
            1,
            "Authorization Bearer abc.def password=hunter2 redis://u:p@redis:6379/0",
            (),
            None,
        )
        payload = json.loads(CloudXJsonFormatter().format(record))
        rendered = payload["message"]
        self.assertNotIn("abc.def", rendered)
        self.assertNotIn("hunter2", rendered)
        self.assertNotIn("u:p", rendered)
        self.assertIn("[REDACTED]", rendered)
        self.assertNotIn("hunter2", redact_log_text("password=hunter2"))


if __name__ == "__main__":
    unittest.main()
