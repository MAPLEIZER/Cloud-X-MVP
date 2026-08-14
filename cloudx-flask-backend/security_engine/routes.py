import re

from flask import Blueprint, jsonify, request

from auth import clerk_authorized
from .base import SecurityEngineNotConfigured, SecurityEngineUpstreamError

_AGENT_ID_RE = re.compile(r"^[0-9]{1,8}$")


def _bounded_limit(default=100, maximum=500):
    raw = request.args.get("limit", str(default))
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if value < 1 or value > maximum:
        return None
    return value


def _agent_id():
    value = request.args.get("agent_id", "")
    return value if _AGENT_ID_RE.fullmatch(value) else None


def create_security_blueprint(engine):
    blueprint = Blueprint("security_engine", __name__, url_prefix="/api/security")

    def execute(operation):
        if engine is None:
            return (
                jsonify(
                    {
                        "error": "Security engine is not configured",
                        "code": "security_engine_not_configured",
                    }
                ),
                503,
            )
        try:
            return jsonify(operation())
        except SecurityEngineNotConfigured:
            return (
                jsonify(
                    {
                        "error": "Security engine capability is not configured",
                        "code": "security_engine_capability_not_configured",
                    }
                ),
                503,
            )
        except SecurityEngineUpstreamError:
            return (
                jsonify(
                    {
                        "error": "Security engine upstream is unavailable",
                        "code": "security_engine_upstream_error",
                    }
                ),
                502,
            )

    @blueprint.get("/status")
    @clerk_authorized
    def security_status():
        return execute(engine.status if engine else lambda: None)

    @blueprint.get("/overview")
    @clerk_authorized
    def security_overview():
        return execute(engine.overview if engine else lambda: None)

    @blueprint.get("/agents")
    @clerk_authorized
    def security_agents():
        limit = _bounded_limit(default=100, maximum=500)
        if limit is None:
            return jsonify({"error": "limit must be between 1 and 500"}), 400
        return execute(lambda: engine.agents(limit=limit) if engine else None)

    @blueprint.get("/alerts")
    @clerk_authorized
    def security_alerts():
        limit = _bounded_limit(default=50, maximum=200)
        if limit is None:
            return jsonify({"error": "limit must be between 1 and 200"}), 400
        return execute(lambda: engine.alerts(limit=limit) if engine else None)

    @blueprint.get("/sca")
    @clerk_authorized
    def security_sca():
        agent_id = _agent_id()
        limit = _bounded_limit(default=100, maximum=500)
        if agent_id is None:
            return jsonify({"error": "agent_id must be a numeric Wazuh agent ID"}), 400
        if limit is None:
            return jsonify({"error": "limit must be between 1 and 500"}), 400
        return execute(
            lambda: engine.sca(agent_id, limit=limit) if engine else None
        )

    @blueprint.get("/fim")
    @clerk_authorized
    def security_fim():
        agent_id = _agent_id()
        limit = _bounded_limit(default=100, maximum=500)
        if agent_id is None:
            return jsonify({"error": "agent_id must be a numeric Wazuh agent ID"}), 400
        if limit is None:
            return jsonify({"error": "limit must be between 1 and 500"}), 400
        return execute(
            lambda: engine.fim(agent_id, limit=limit) if engine else None
        )

    return blueprint
