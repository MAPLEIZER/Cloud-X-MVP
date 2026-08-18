"""Privacy-first error tracking for a self-hosted Sentry-compatible backend.

Cloud-X is tested against GlitchTip, an MIT-licensed self-hostable error tracking
service. The integration intentionally uses the generic Sentry ingestion
protocol/SDK so the application does not depend on GlitchTip-specific APIs.

No request bodies, cookies, authorization headers, query strings, local frame
variables, or provider credentials are forwarded by this module.
"""

from __future__ import annotations

import copy
import os
from urllib.parse import urlsplit, urlunsplit

from flask import Blueprint, jsonify, request
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.rq import RqIntegration

from observability import redact_log_text

_INITIALIZED = False
_ENABLED = False


def _sample_rate(name: str, default: float = 0.0) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number between 0 and 1") from exc
    if value < 0 or value > 1:
        raise RuntimeError(f"{name} must be between 0 and 1")
    return value


def _validate_dsn(value: str) -> str:
    dsn = value.strip()
    if not dsn:
        return ""
    parsed = urlsplit(dsn)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError("ERROR_TRACKING_DSN must be an HTTP(S) Sentry-compatible DSN")
    return dsn


def _strip_url_query(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return redact_log_text(value)
    if parsed.scheme and parsed.netloc:
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))
    return redact_log_text(value.split("?", 1)[0].split("#", 1)[0])


def _scrub_value(value):
    if isinstance(value, str):
        return redact_log_text(value)
    if isinstance(value, list):
        return [_scrub_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_scrub_value(item) for item in value)
    if isinstance(value, dict):
        return {key: _scrub_value(item) for key, item in value.items()}
    return value


def _remove_frame_variables(event: dict) -> None:
    exception = event.get("exception")
    if not isinstance(exception, dict):
        return
    values = exception.get("values")
    if not isinstance(values, list):
        return
    for item in values:
        if not isinstance(item, dict):
            continue
        stacktrace = item.get("stacktrace")
        if not isinstance(stacktrace, dict):
            continue
        frames = stacktrace.get("frames")
        if not isinstance(frames, list):
            continue
        for frame in frames:
            if isinstance(frame, dict):
                frame.pop("vars", None)


def scrub_event(event: dict, hint=None):
    """Remove high-risk request/credential material before an event leaves Cloud-X."""

    del hint
    cleaned = copy.deepcopy(event)

    request_data = cleaned.get("request")
    if isinstance(request_data, dict):
        request_data.pop("headers", None)
        request_data.pop("cookies", None)
        request_data.pop("data", None)
        request_data.pop("query_string", None)
        url = request_data.get("url")
        if isinstance(url, str):
            request_data["url"] = _strip_url_query(url)

    _remove_frame_variables(cleaned)

    for key in ("message", "extra", "contexts", "exception", "breadcrumbs"):
        if key in cleaned:
            cleaned[key] = _scrub_value(cleaned[key])

    user = cleaned.get("user")
    if isinstance(user, dict):
        # Do not transmit email, username, IP address or arbitrary user metadata.
        allowed_id = user.get("id") if os.getenv("ERROR_TRACKING_INCLUDE_USER_ID") == "true" else None
        cleaned["user"] = {"id": redact_log_text(allowed_id)} if allowed_id else {}

    return cleaned


def init_error_tracking(*, component: str, flask: bool = False, rq: bool = False) -> bool:
    """Initialize the Sentry-compatible SDK once per process when a DSN is configured."""

    global _INITIALIZED, _ENABLED
    if _INITIALIZED:
        return _ENABLED

    dsn = _validate_dsn(os.getenv("ERROR_TRACKING_DSN", ""))
    _INITIALIZED = True
    if not dsn:
        _ENABLED = False
        return False

    integrations = []
    if flask:
        integrations.append(FlaskIntegration())
    if rq:
        integrations.append(RqIntegration())

    sentry_sdk.init(
        dsn=dsn,
        environment=os.getenv("ERROR_TRACKING_ENVIRONMENT", "production"),
        release=os.getenv("ERROR_TRACKING_RELEASE") or None,
        traces_sample_rate=_sample_rate("ERROR_TRACKING_TRACES_SAMPLE_RATE", 0.0),
        send_default_pii=False,
        max_request_body_size="never",
        auto_session_tracking=False,
        attach_stacktrace=True,
        before_send=scrub_event,
        integrations=integrations,
    )
    sentry_sdk.set_tag("cloudx_component", component)
    _ENABLED = True
    return True


def is_error_tracking_enabled() -> bool:
    return _ENABLED


def _safe_text(value, *, maximum: int) -> str:
    if not isinstance(value, str):
        return ""
    return redact_log_text(value.strip())[:maximum]


def _safe_path(value) -> str:
    if not isinstance(value, str):
        return ""
    value = value.strip().split("?", 1)[0].split("#", 1)[0]
    if not value.startswith("/"):
        return ""
    return redact_log_text(value)[:1024]


def capture_frontend_error(payload: dict) -> None:
    """Forward a sanitized browser error through the configured GlitchTip DSN."""

    message = _safe_text(payload.get("message"), maximum=2048) or "Frontend runtime error"
    error_name = _safe_text(payload.get("name"), maximum=128) or "Error"
    stack = _safe_text(payload.get("stack"), maximum=12000)
    source = _safe_text(payload.get("source"), maximum=64) or "frontend"
    path = _safe_path(payload.get("path"))

    sentry_sdk.capture_event(
        {
            "level": "error",
            "message": {"formatted": message},
            "tags": {
                "cloudx_source": "frontend",
                "frontend_error_name": error_name,
                "frontend_error_source": source,
            },
            "extra": {
                "frontend_stack": stack or None,
                "frontend_path": path or None,
                "line": payload.get("line") if isinstance(payload.get("line"), int) else None,
                "column": payload.get("column") if isinstance(payload.get("column"), int) else None,
            },
        }
    )


def create_error_tracking_blueprint(auth_decorator) -> Blueprint:
    """Authenticated frontend-to-GlitchTip bridge.

    The endpoint intentionally never accepts arbitrary tags, user objects, request
    headers, cookies or URLs. This keeps the browser collector small and prevents
    authenticated users from turning Cloud-X into a generic telemetry relay.
    """

    blueprint = Blueprint("error_tracking", __name__)

    @blueprint.post("/api/client-errors")
    @auth_decorator
    def client_error():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "A JSON object is required"}), 400

        message = payload.get("message")
        if not isinstance(message, str) or not message.strip():
            return jsonify({"error": "message is required"}), 400

        capture_frontend_error(payload)
        return jsonify({"status": "accepted"}), 202

    return blueprint
