"""Production application assembly for Cloud-X.

`app.py` retains the core Flask application/model definitions used by Alembic and
unit tests. This module attaches optional provider adapters before Gunicorn
serves the application, keeping Wazuh-specific wiring out of the core domain.
"""

from app import app
from security_engine import WazuhSecurityEngine, create_security_blueprint
from security_engine.wazuh_metrics import WazuhSystemMetricsProvider
from system_metrics import create_system_monitor_view

security_engine = WazuhSecurityEngine.from_env()
app.register_blueprint(create_security_blueprint(security_engine))

metrics_provider = (
    WazuhSystemMetricsProvider(security_engine) if security_engine is not None else None
)

# Replace the legacy prototype view with the production monitor contract. The
# registered URL/endpoint remains `/api/system-monitor` / `system_monitor`, so
# existing clients keep working while production stops emitting generated data.
app.view_functions["system_monitor"] = create_system_monitor_view(metrics_provider)

__all__ = ["app", "security_engine", "metrics_provider"]
