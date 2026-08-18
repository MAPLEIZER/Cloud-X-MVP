import logging
import os
from dataclasses import dataclass
from functools import wraps

import jwt
from flask import current_app, g, jsonify, request

from security_utils import (
    is_deployment_target_allowed,
    is_valid_host,
    parse_deployment_target_allowlist,
)

logger = logging.getLogger(__name__)

try:
    DEPLOYMENT_TARGET_ALLOWLIST = parse_deployment_target_allowlist(
        os.getenv("DEPLOYMENT_TARGET_ALLOWLIST_JSON")
    )
except ValueError as exc:
    raise RuntimeError("Invalid deployment target allow-list configuration") from exc

WINDOWS_AGENT_DEPLOYMENT_ENABLED = os.getenv(
    "ENABLE_WINDOWS_AGENT_DEPLOYMENT", "false"
).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class RequestAuthState:
    """Minimal request-auth state retained for internal compatibility."""

    is_signed_in: bool
    payload: dict


def _extract_session_token(flask_request):
    """Return a Clerk session token from Bearer auth or the same-origin cookie."""

    authorization = flask_request.headers.get("Authorization", "").strip()
    if authorization:
        scheme, separator, token = authorization.partition(" ")
        if separator and scheme.lower() == "bearer" and token.strip():
            return token.strip()
        raise jwt.InvalidTokenError("Malformed Authorization header")

    cookie_token = flask_request.cookies.get("__session")
    if isinstance(cookie_token, str) and cookie_token.strip():
        return cookie_token.strip()
    return None


def authenticate_request(flask_request, *, jwt_key, authorized_parties):
    """Verify a Clerk session JWT using the instance PEM public key.

    Cloud-X intentionally performs networkless verification instead of importing
    Clerk's generated Python SDK. Clerk documents manual verification as a
    supported path: verify RS256, expiration/not-before, and the `azp` claim
    against the trusted frontend origins. This keeps request authentication
    independent of the Clerk SDK's cryptography version ceiling.
    """

    token = _extract_session_token(flask_request)
    if not token:
        return RequestAuthState(is_signed_in=False, payload={})

    header = jwt.get_unverified_header(token)
    if header.get("alg") != "RS256":
        raise jwt.InvalidAlgorithmError("Clerk session tokens must use RS256")
    if header.get("typ") not in {None, "JWT"}:
        raise jwt.InvalidTokenError("Unexpected JWT header type")

    payload = jwt.decode(
        token,
        jwt_key,
        algorithms=["RS256"],
        options={
            "require": ["exp", "nbf", "sub", "iss"],
            # Cloud-X does not currently configure a Clerk JWT audience. PyJWT
            # otherwise rejects any token that happens to contain `aud` when no
            # expected audience is supplied.
            "verify_aud": False,
        },
        leeway=5,
    )

    authorized_party = payload.get("azp")
    if authorized_party is not None and authorized_party not in authorized_parties:
        raise jwt.InvalidTokenError("Unauthorized Clerk token party")

    # Clerk documents `sts=pending` for sessions that have not satisfied an
    # organization requirement. Fail closed rather than treating that token as
    # a fully signed-in control-plane session.
    if payload.get("sts") == "pending":
        raise jwt.InvalidTokenError("Clerk session is pending")

    return RequestAuthState(is_signed_in=True, payload=payload)


def _active_org_id(payload):
    """Read the active Clerk organization ID from v2 or legacy token claims."""

    if not isinstance(payload, dict):
        return None

    compact_org = payload.get("o")
    if isinstance(compact_org, dict):
        org_id = compact_org.get("id")
        if isinstance(org_id, str) and org_id:
            return org_id

    org_id = payload.get("org_id")
    if isinstance(org_id, str) and org_id:
        return org_id
    return None


def _deployment_policy_error(user_id, org_id):
    """Return an endpoint-specific deployment authorization error, if any."""

    if request.endpoint != "deploy_agent":
        return None

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        # app.py owns request-shape validation and returns the canonical 400.
        return None

    target = data.get("target")
    if is_valid_host(target) and not is_deployment_target_allowed(
        target,
        user_id,
        org_id,
        DEPLOYMENT_TARGET_ALLOWLIST,
    ):
        logger.warning(
            "Rejected deployment outside configured target allow-list for user %s",
            user_id,
        )
        return jsonify({"error": "Deployment target is not authorized"}), 403

    if data.get("os_type") == "windows" and not WINDOWS_AGENT_DEPLOYMENT_ENABLED:
        return (
            jsonify(
                {
                    "error": "Windows agent deployment is disabled",
                    "reason": "Enable it explicitly after validating WinRM in your environment.",
                }
            ),
            503,
        )

    return None


def clerk_authorized(view):
    """Require a valid Clerk session from an explicitly allowed Cloud-X user."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        try:
            state = authenticate_request(
                request,
                jwt_key=current_app.config["CLERK_JWT_KEY"],
                authorized_parties=current_app.config["CLERK_AUTHORIZED_PARTIES"],
            )
        except (jwt.PyJWTError, ValueError, TypeError):
            logger.warning("Clerk request authentication failed")
            return jsonify({"error": "Authentication failed"}), 401

        if not state.is_signed_in:
            return (
                jsonify({"error": "Authentication required"}),
                401,
                {"WWW-Authenticate": "Bearer"},
            )

        payload = state.payload or {}
        user_id = payload.get("sub") if isinstance(payload, dict) else None
        allowed_user_ids = current_app.config["CLERK_ALLOWED_USER_IDS"]

        if not user_id or user_id not in allowed_user_ids:
            logger.warning("Rejected authenticated but unauthorized Clerk user")
            return jsonify({"error": "Forbidden"}), 403

        org_id = _active_org_id(payload)
        g.auth_state = state
        g.user_id = user_id
        g.org_id = org_id

        deployment_error = _deployment_policy_error(user_id, org_id)
        if deployment_error is not None:
            return deployment_error

        return view(*args, **kwargs)

    return wrapper
