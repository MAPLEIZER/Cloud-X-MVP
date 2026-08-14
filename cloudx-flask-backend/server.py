"""Production application assembly for Cloud-X.

`app.py` retains the core Flask application/model definitions used by Alembic and
unit tests. This module attaches optional provider adapters before Gunicorn
serves the application, keeping Wazuh-specific wiring out of the core domain.
"""

from app import app
from security_engine import WazuhSecurityEngine, create_security_blueprint

security_engine = WazuhSecurityEngine.from_env()
app.register_blueprint(create_security_blueprint(security_engine))

__all__ = ["app", "security_engine"]
