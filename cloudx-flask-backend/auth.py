import logging
from functools import wraps

from clerk_backend_api import AuthenticateRequestOptions, authenticate_request
from flask import current_app, g, jsonify, request

logger = logging.getLogger(__name__)


def clerk_authorized(view):
    """Require a valid Clerk session from an explicitly allowed Cloud-X user."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        try:
            state = authenticate_request(
                request,
                AuthenticateRequestOptions(
                    secret_key=current_app.config.get("CLERK_SECRET_KEY"),
                    jwt_key=current_app.config.get("CLERK_JWT_KEY"),
                    authorized_parties=current_app.config["CLERK_AUTHORIZED_PARTIES"],
                    accepts_token=["session_token"],
                ),
            )
        except Exception:
            logger.exception("Clerk request authentication failed")
            return jsonify({"error": "Authentication failed"}), 401

        if not state.is_signed_in:
            return (
                jsonify({"error": "Authentication required"}),
                401,
                {"WWW-Authenticate": "Bearer"},
            )

        payload = state.payload or {}
        user_id = payload.get("sub")
        allowed_user_ids = current_app.config["CLERK_ALLOWED_USER_IDS"]

        if not user_id or user_id not in allowed_user_ids:
            logger.warning("Rejected authenticated but unauthorized Clerk user")
            return jsonify({"error": "Forbidden"}), 403

        g.auth_state = state
        g.user_id = user_id
        return view(*args, **kwargs)

    return wrapper
