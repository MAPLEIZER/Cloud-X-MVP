"""Production application assembly for Cloud-X.

`app.py` retains the core Flask application/model definitions used by Alembic and
unit tests. This module attaches production adapters and observability before
Gunicorn serves the application, keeping provider-specific wiring out of the
core domain.
"""

from error_tracking import (
    create_error_tracking_blueprint,
    init_error_tracking,
    is_error_tracking_enabled,
)

# Initialize the Sentry-compatible SDK before importing/creating the Flask app so
# FlaskIntegration can instrument request failures. With no DSN this is a no-op.
init_error_tracking(component="api", flask=True)

from app import app, db
from auth import clerk_authorized
from observability import (
    configure_json_logging,
    create_health_blueprint,
    install_request_observability,
)
from scan_queue import assert_queue_available
from security_engine import WazuhSecurityEngine, create_security_blueprint
from security_engine.wazuh_metrics import WazuhSystemMetricsProvider
from system_metrics import create_system_monitor_view

configure_json_logging()
install_request_observability(app)
app.register_blueprint(create_error_tracking_blueprint(clerk_authorized))

security_engine = WazuhSecurityEngine.from_env()
app.register_blueprint(create_security_blueprint(security_engine))
app.register_blueprint(
    create_health_blueprint(
        db,
        assert_queue_available,
        security_engine=security_engine,
    )
)

metrics_provider = (
    WazuhSystemMetricsProvider(security_engine) if security_engine is not None else None
)

# Replace the legacy prototype view with the production monitor contract. The
# registered URL/endpoint remains `/api/system-monitor` / `system_monitor`, so
# existing clients keep working while production stops emitting generated data.
app.view_functions["system_monitor"] = create_system_monitor_view(metrics_provider)

__all__ = [
    "app",
    "security_engine",
    "metrics_provider",
    "is_error_tracking_enabled",
]
