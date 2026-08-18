"""Production observability primitives for the Cloud-X API.

This module deliberately avoids logging request bodies, query strings, cookies,
authorization headers, or provider credentials. It provides request-correlated
JSON logs plus liveness/readiness probes that can be consumed by Compose,
reverse proxies, and later orchestration platforms.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
import re
import time
import uuid

from flask import Blueprint, g, jsonify, request
from sqlalchemy import text

_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_SECRET_KV_RE = re.compile(
    r"(?i)\b(password|passwd|secret|token|api[_-]?key)\b\s*[:=]\s*([^\s,;]+)"
)
_URI_CREDENTIAL_RE = re.compile(
    r"(?P<scheme>\b[a-z][a-z0-9+.-]*://)(?P<creds>[^/@\s]+@)", re.I
)


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def redact_log_text(value: object) -> str:
    """Apply defense-in-depth redaction to free-form log text.

    Structured request logging never includes sensitive request fields in the
    first place. This helper protects accidental secrets that might still reach
    ordinary application log messages or exception text.
    """

    text_value = str(value)
    text_value = _BEARER_RE.sub("Bearer [REDACTED]", text_value)
    text_value = _SECRET_KV_RE.sub(lambda m: f"{m.group(1)}=[REDACTED]", text_value)
    text_value = _URI_CREDENTIAL_RE.sub(
        lambda m: f"{m.group('scheme')}[REDACTED]@", text_value
    )
    return text_value


class CloudXJsonFormatter(logging.Formatter):
    """Small JSON formatter with a stable, ingestion-friendly schema."""

    _extra_fields = (
        "request_id",
        "method",
        "path",
        "status_code",
        "duration_ms",
        "component",
        "event",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": _utc_timestamp(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": redact_log_text(record.getMessage()),
        }
        for field in self._extra_fields:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = redact_log_text(self.formatException(record.exc_info))
        return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)


def configure_json_logging() -> None:
    """Configure the root logger once for container-friendly JSON output."""

    raw_level = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, raw_level, logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)

    if not any(getattr(handler, "_cloudx_json", False) for handler in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(CloudXJsonFormatter())
        handler._cloudx_json = True  # type: ignore[attr-defined]
        root.addHandler(handler)

    # Avoid mixed plain-text + JSON output from logging.basicConfig or framework
    # defaults when this module is imported by Gunicorn or the test suite.
    for handler in list(root.handlers):
        if not getattr(handler, "_cloudx_json", False):
            root.removeHandler(handler)


def _request_id_from_header() -> str:
    candidate = request.headers.get("X-Request-ID", "").strip()
    if candidate and _REQUEST_ID_RE.fullmatch(candidate):
        return candidate
    return str(uuid.uuid4())


def install_request_observability(app) -> None:
    """Attach request IDs and one structured completion record per request."""

    request_logger = logging.getLogger("cloudx.request")
    app.logger.handlers.clear()
    app.logger.propagate = True

    @app.before_request
    def _start_request_observation():
        g.request_id = _request_id_from_header()
        g.request_started_at = time.perf_counter()

    @app.after_request
    def _finish_request_observation(response):
        request_id = getattr(g, "request_id", str(uuid.uuid4()))
        started_at = getattr(g, "request_started_at", None)
        duration_ms = None
        if started_at is not None:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)

        response.headers["X-Request-ID"] = request_id
        request_logger.info(
            "request_complete",
            extra={
                "event": "request_complete",
                "request_id": request_id,
                "method": request.method,
                # Intentionally omit query strings, request bodies and headers.
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        return response

    @app.teardown_request
    def _record_unhandled_request_exception(error):
        if error is None:
            return
        request_logger.error(
            "request_exception",
            exc_info=(type(error), error, error.__traceback__),
            extra={
                "event": "request_exception",
                "request_id": getattr(g, "request_id", None),
                "method": request.method,
                "path": request.path,
            },
        )


def create_health_blueprint(db, queue_probe, security_engine=None) -> Blueprint:
    """Create liveness/readiness probes without exposing dependency secrets.

    PostgreSQL and Redis/RQ are required for API readiness. Wazuh is reported as
    an optional/degraded component because Cloud-X must keep serving scan and
    administrative APIs during a Manager/Indexer outage.
    """

    blueprint = Blueprint("observability_health", __name__)

    @blueprint.get("/api/health/live")
    def liveness():
        return jsonify(
            {
                "status": "ok",
                "service": "cloudx-api",
                "timestamp": _utc_timestamp(),
            }
        ), 200

    @blueprint.get("/api/health/ready")
    def readiness():
        components = {}
        required_ready = True

        try:
            db.session.execute(text("SELECT 1"))
            components["postgres"] = {"status": "ok", "required": True}
        except Exception:  # noqa: BLE001 - a probe must normalize driver failures.
            required_ready = False
            components["postgres"] = {"status": "unavailable", "required": True}
            try:
                db.session.rollback()
            except Exception:  # noqa: BLE001
                pass

        try:
            queue_probe()
            components["redis_queue"] = {"status": "ok", "required": True}
        except Exception:  # noqa: BLE001 - never expose Redis URL/exception details.
            required_ready = False
            components["redis_queue"] = {"status": "unavailable", "required": True}

        degraded = False
        if security_engine is None:
            components["security_engine"] = {
                "status": "not_configured",
                "required": False,
            }
        else:
            try:
                engine_status = security_engine.status()
                manager_connected = bool(engine_status.get("manager_connected"))
                indexer_configured = bool(engine_status.get("indexer_configured", False))
                indexer_status = str(engine_status.get("indexer_status") or "").lower()
                indexer_healthy = not indexer_configured or indexer_status in {
                    "green",
                    "yellow",
                }
                engine_ok = manager_connected and indexer_healthy
                if not engine_ok:
                    degraded = True
                components["security_engine"] = {
                    "status": "ok" if engine_ok else "degraded",
                    "required": False,
                }
            except Exception:  # noqa: BLE001 - health output must stay credential-safe.
                degraded = True
                components["security_engine"] = {
                    "status": "unavailable",
                    "required": False,
                }

        http_status = 200 if required_ready else 503
        if not required_ready:
            status = "not_ready"
        elif degraded:
            status = "degraded"
        else:
            status = "ready"

        return jsonify(
            {
                "status": status,
                "ready": required_ready,
                "timestamp": _utc_timestamp(),
                "components": components,
            }
        ), http_status

    return blueprint
