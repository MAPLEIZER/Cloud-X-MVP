import ipaddress
import json
import re
from urllib.parse import urlparse

_HOST_LABEL_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_PRINCIPAL_RE = re.compile(r"^(?:user|org):[A-Za-z0-9_-]{1,128}$")


def _clean_string(value, max_length=253):
    if not isinstance(value, str):
        return None
    if value != value.strip() or not value or len(value) > max_length:
        return None
    if any(char.isspace() for char in value) or value.startswith("-"):
        return None
    return value


def is_valid_hostname(value):
    value = _clean_string(value)
    if value is None:
        return False

    host = value[:-1] if value.endswith(".") else value
    if not host or len(host) > 253:
        return False

    labels = host.split(".")
    return all(_HOST_LABEL_RE.fullmatch(label) for label in labels)


def is_valid_host(value):
    value = _clean_string(value)
    if value is None:
        return False

    try:
        ipaddress.ip_address(value)
        return True
    except ValueError:
        return is_valid_hostname(value)


def is_valid_scan_target(value):
    value = _clean_string(value)
    if value is None:
        return False

    if "/" in value:
        try:
            ipaddress.ip_network(value, strict=False)
            return True
        except ValueError:
            return False

    return is_valid_host(value)


def is_valid_identifier(value):
    if not isinstance(value, str):
        return False
    return bool(_IDENTIFIER_RE.fullmatch(value))


def is_valid_known_hosts_line(value):
    if value is None:
        return True
    if not isinstance(value, str) or not value or len(value) > 8192:
        return False
    return "\n" not in value and "\r" not in value


def parse_origin_csv(value):
    origins = []
    for item in (value or "").split(","):
        origin = item.strip().rstrip("/")
        if not origin:
            continue

        parsed = urlparse(origin)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.path not in {"", "/"}
            or parsed.params
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(f"Invalid origin: {item!r}")

        origins.append(origin)

    return origins


def parse_csv(value):
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def _normalize_allowlist_entry(value):
    value = _clean_string(value)
    if value is None:
        raise ValueError("Deployment allow-list entries must be non-empty strings")

    if "/" in value:
        try:
            return str(ipaddress.ip_network(value, strict=False))
        except ValueError as exc:
            raise ValueError(f"Invalid deployment network: {value!r}") from exc

    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        if not is_valid_hostname(value):
            raise ValueError(f"Invalid deployment host: {value!r}")
        return value.rstrip(".").lower()


def parse_deployment_target_allowlist(value):
    """Parse a fail-closed user/org deployment target allow-list.

    Shape:
      {"user:user_123": ["10.0.0.0/24", "host.example.com"],
       "org:org_123": ["192.0.2.10"]}

    CIDRs only authorize literal IP targets. Hostnames must be listed exactly,
    avoiding DNS-resolution based authorization and DNS-rebinding surprises.
    """

    if value is None or not str(value).strip():
        return {}

    try:
        raw = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("DEPLOYMENT_TARGET_ALLOWLIST_JSON must be valid JSON") from exc

    if not isinstance(raw, dict):
        raise ValueError("Deployment allow-list must be a JSON object")
    if len(raw) > 1024:
        raise ValueError("Deployment allow-list contains too many principals")

    parsed = {}
    for principal, entries in raw.items():
        if not isinstance(principal, str) or not _PRINCIPAL_RE.fullmatch(principal):
            raise ValueError(f"Invalid deployment principal: {principal!r}")
        if not isinstance(entries, list):
            raise ValueError(f"Deployment targets for {principal!r} must be a list")
        if len(entries) > 1024:
            raise ValueError(f"Too many deployment targets for {principal!r}")

        normalized = []
        seen = set()
        for entry in entries:
            normalized_entry = _normalize_allowlist_entry(entry)
            if normalized_entry not in seen:
                normalized.append(normalized_entry)
                seen.add(normalized_entry)
        parsed[principal] = tuple(normalized)

    return parsed


def is_deployment_target_allowed(target, user_id, org_id, allowlist):
    if not is_valid_host(target) or not isinstance(allowlist, dict):
        return False

    principals = []
    if isinstance(user_id, str) and user_id:
        principals.append(f"user:{user_id}")
    if isinstance(org_id, str) and org_id:
        principals.append(f"org:{org_id}")

    entries = []
    for principal in principals:
        entries.extend(allowlist.get(principal, ()))

    try:
        target_ip = ipaddress.ip_address(target)
    except ValueError:
        target_ip = None
        normalized_hostname = target.rstrip(".").lower()

    for entry in entries:
        if "/" in entry:
            if target_ip is None:
                continue
            if target_ip in ipaddress.ip_network(entry, strict=False):
                return True
            continue

        try:
            allowed_ip = ipaddress.ip_address(entry)
        except ValueError:
            if target_ip is None and normalized_hostname == entry.rstrip(".").lower():
                return True
        else:
            if target_ip is not None and target_ip == allowed_ip:
                return True

    return False
