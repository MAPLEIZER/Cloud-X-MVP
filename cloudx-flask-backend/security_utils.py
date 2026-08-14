import ipaddress
import re
from urllib.parse import urlparse

_HOST_LABEL_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


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
