import base64
import json
import os
import ssl
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from .base import SecurityEngine, SecurityEngineNotConfigured, SecurityEngineUpstreamError


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def _bool_env(name, default=True):
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise RuntimeError(f"{name} must be a boolean value")


def _positive_int_env(name, default, maximum):
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value < 1 or value > maximum:
        raise RuntimeError(f"{name} must be between 1 and {maximum}")
    return value


def _validate_api_url(name, value):
    if not value:
        return None
    value = value.strip().rstrip("/")
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError(f"{name} must be an HTTPS URL without credentials/query/fragment")
    return value


def _ssl_context(verify_tls, ca_bundle):
    if not verify_tls:
        return ssl._create_unverified_context()  # noqa: SLF001 - explicit operator opt-out
    if ca_bundle:
        return ssl.create_default_context(cafile=ca_bundle)
    return ssl.create_default_context()


class _HttpClient:
    def __init__(
        self,
        base_url,
        timeout_seconds,
        verify_tls=True,
        ca_bundle=None,
        max_response_bytes=5 * 1024 * 1024,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.context = _ssl_context(verify_tls, ca_bundle)
        self.max_response_bytes = max_response_bytes

    def request(
        self,
        method,
        path,
        *,
        query=None,
        json_body=None,
        headers=None,
        basic_auth=None,
        raw=False,
    ):
        url = f"{self.base_url}/{path.lstrip('/')}"
        if query:
            url = f"{url}?{urlencode(query, doseq=True)}"

        request_headers = {"Accept": "application/json"}
        if headers:
            request_headers.update(headers)
        if basic_auth:
            username, password = basic_auth
            token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
            request_headers["Authorization"] = f"Basic {token}"

        data = None
        if json_body is not None:
            data = json.dumps(json_body, separators=(",", ":")).encode("utf-8")
            request_headers["Content-Type"] = "application/json"

        request = Request(url, data=data, headers=request_headers, method=method)
        try:
            response = urlopen(
                request,
                timeout=self.timeout_seconds,
                context=self.context,
            )
            status = getattr(response, "status", 200)
            payload = response.read(self.max_response_bytes + 1)
        except HTTPError as exc:
            status = exc.code
            try:
                payload = exc.read(8192)
            except Exception:
                payload = b""
            raise SecurityEngineUpstreamError(
                f"Upstream HTTP request failed with status {status}",
                status_code=status,
            ) from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise SecurityEngineUpstreamError("Security engine upstream is unreachable") from exc

        if len(payload) > self.max_response_bytes:
            raise SecurityEngineUpstreamError("Security engine response exceeded the size limit")
        if status < 200 or status >= 300:
            raise SecurityEngineUpstreamError(
                f"Upstream HTTP request failed with status {status}",
                status_code=status,
            )

        text = payload.decode("utf-8", errors="strict")
        if raw:
            return text.strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise SecurityEngineUpstreamError("Security engine returned invalid JSON") from exc


class _WazuhServerClient:
    def __init__(self, http, username, password):
        self.http = http
        self.username = username
        self.password = password
        self._token = None
        self._token_lock = threading.Lock()

    def _authenticate(self):
        token = self.http.request(
            "POST",
            "/security/user/authenticate",
            query={"raw": "true"},
            basic_auth=(self.username, self.password),
            raw=True,
        )
        if not token or len(token) > 16384:
            raise SecurityEngineUpstreamError("Wazuh server API returned an invalid JWT")
        return token

    def _get_token(self, force_refresh=False):
        with self._token_lock:
            if force_refresh or not self._token:
                self._token = self._authenticate()
            return self._token

    def get(self, path, query=None):
        for attempt in range(2):
            token = self._get_token(force_refresh=attempt == 1)
            try:
                return self.http.request(
                    "GET",
                    path,
                    query=query,
                    headers={"Authorization": f"Bearer {token}"},
                )
            except SecurityEngineUpstreamError as exc:
                if exc.status_code == 401 and attempt == 0:
                    continue
                raise
        raise SecurityEngineUpstreamError("Wazuh server API authentication failed")


class _WazuhIndexerClient:
    def __init__(self, http, username, password):
        self.http = http
        self.username = username
        self.password = password

    def search_alerts(self, limit):
        body = {
            "size": limit,
            "sort": [{"timestamp": {"order": "desc", "unmapped_type": "date"}}],
            "query": {"match_all": {}},
            "_source": [
                "timestamp",
                "rule.id",
                "rule.level",
                "rule.description",
                "rule.groups",
                "rule.mitre.id",
                "agent.id",
                "agent.name",
                "agent.ip",
                "manager.name",
                "location",
            ],
        }
        return self.http.request(
            "POST",
            "/wazuh-alerts*/_search",
            json_body=body,
            basic_auth=(self.username, self.password),
        )

    def health(self):
        return self.http.request(
            "GET",
            "/_cluster/health",
            basic_auth=(self.username, self.password),
        )


def _affected_items(payload):
    if not isinstance(payload, dict):
        return []
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    items = data.get("affected_items")
    return items if isinstance(items, list) else []


def _normalise_agent(item):
    os_data = item.get("os") if isinstance(item.get("os"), dict) else {}
    group = item.get("group")
    if isinstance(group, str):
        groups = [entry for entry in group.split(",") if entry]
    elif isinstance(group, list):
        groups = [str(entry) for entry in group]
    else:
        groups = []

    return {
        "id": str(item.get("id", "")),
        "name": str(item.get("name", "Unknown agent")),
        "ip": item.get("ip"),
        "status": str(item.get("status", "unknown")).lower(),
        "groups": groups,
        "version": item.get("version"),
        "node": item.get("node_name"),
        "last_seen": item.get("lastKeepAlive"),
        "os": {
            "name": os_data.get("name"),
            "version": os_data.get("version"),
            "platform": os_data.get("platform"),
            "arch": os_data.get("arch"),
        },
    }


def _normalise_sca(item):
    passed = int(item.get("pass", 0) or 0)
    failed = int(item.get("fail", 0) or 0)
    invalid = int(item.get("invalid", 0) or 0)
    total = int(item.get("total_checks", passed + failed + invalid) or 0)
    score = item.get("score")
    try:
        score = float(score) if score is not None else None
    except (TypeError, ValueError):
        score = None
    return {
        "policy_id": str(item.get("policy_id", item.get("id", ""))),
        "name": item.get("name") or item.get("description") or "SCA policy",
        "description": item.get("description"),
        "passed": passed,
        "failed": failed,
        "invalid": invalid,
        "total": total,
        "score": score,
        "last_scan": item.get("end_scan") or item.get("start_scan"),
    }


def _normalise_fim(item):
    return {
        "path": item.get("file") or item.get("path"),
        "type": item.get("type"),
        "size": item.get("size"),
        "permissions": item.get("perm"),
        "owner": item.get("uname") or item.get("uid"),
        "group": item.get("gname") or item.get("gid"),
        "sha256": item.get("sha256"),
        "changes": int(item.get("changes", 0) or 0),
        "modified_at": item.get("mtime"),
        "observed_at": item.get("date"),
    }


def _normalise_alert(hit):
    source = hit.get("_source") if isinstance(hit, dict) else {}
    if not isinstance(source, dict):
        source = {}
    rule = source.get("rule") if isinstance(source.get("rule"), dict) else {}
    agent = source.get("agent") if isinstance(source.get("agent"), dict) else {}
    manager = source.get("manager") if isinstance(source.get("manager"), dict) else {}
    mitre = rule.get("mitre") if isinstance(rule.get("mitre"), dict) else {}
    groups = rule.get("groups") if isinstance(rule.get("groups"), list) else []
    mitre_ids = mitre.get("id") if isinstance(mitre.get("id"), list) else []

    try:
        level = int(rule.get("level", 0) or 0)
    except (TypeError, ValueError):
        level = 0

    return {
        "id": str(hit.get("_id", "")),
        "timestamp": source.get("timestamp"),
        "level": level,
        "rule_id": str(rule.get("id", "")),
        "description": rule.get("description") or "Wazuh alert",
        "groups": [str(group) for group in groups],
        "mitre_ids": [str(value) for value in mitre_ids],
        "agent": {
            "id": str(agent.get("id", "")),
            "name": agent.get("name"),
            "ip": agent.get("ip"),
        },
        "manager": manager.get("name"),
        "location": source.get("location"),
    }


class WazuhSecurityEngine(SecurityEngine):
    def __init__(self, server_client, indexer_client, cache_ttl_seconds=15):
        self.server_client = server_client
        self.indexer_client = indexer_client
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache = {}
        self._cache_lock = threading.Lock()

    @classmethod
    def from_env(cls):
        server_url = _validate_api_url("WAZUH_API_URL", os.getenv("WAZUH_API_URL"))
        server_username = os.getenv("WAZUH_API_USERNAME")
        server_password = os.getenv("WAZUH_API_PASSWORD")

        server_values = (server_url, server_username, server_password)
        if not any(server_values):
            return None
        if not all(server_values):
            raise RuntimeError(
                "WAZUH_API_URL, WAZUH_API_USERNAME and WAZUH_API_PASSWORD must be configured together"
            )

        timeout = _positive_int_env("WAZUH_REQUEST_TIMEOUT_SECONDS", 10, 120)
        cache_ttl = _positive_int_env("WAZUH_CACHE_TTL_SECONDS", 15, 300)
        server_http = _HttpClient(
            server_url,
            timeout,
            verify_tls=_bool_env("WAZUH_API_VERIFY_TLS", True),
            ca_bundle=os.getenv("WAZUH_API_CA_BUNDLE") or None,
        )
        server_client = _WazuhServerClient(server_http, server_username, server_password)

        indexer_url = _validate_api_url(
            "WAZUH_INDEXER_URL", os.getenv("WAZUH_INDEXER_URL")
        )
        indexer_username = os.getenv("WAZUH_INDEXER_USERNAME")
        indexer_password = os.getenv("WAZUH_INDEXER_PASSWORD")
        indexer_values = (indexer_url, indexer_username, indexer_password)

        if any(indexer_values) and not all(indexer_values):
            raise RuntimeError(
                "WAZUH_INDEXER_URL, WAZUH_INDEXER_USERNAME and WAZUH_INDEXER_PASSWORD must be configured together"
            )

        indexer_client = None
        if all(indexer_values):
            indexer_http = _HttpClient(
                indexer_url,
                timeout,
                verify_tls=_bool_env("WAZUH_INDEXER_VERIFY_TLS", True),
                ca_bundle=os.getenv("WAZUH_INDEXER_CA_BUNDLE") or None,
            )
            indexer_client = _WazuhIndexerClient(
                indexer_http, indexer_username, indexer_password
            )

        return cls(server_client, indexer_client, cache_ttl_seconds=cache_ttl)

    def _cached(self, key, loader):
        now = time.monotonic()
        with self._cache_lock:
            cached = self._cache.get(key)
            if cached and cached[0] > now:
                return cached[1]

        value = loader()
        with self._cache_lock:
            self._cache[key] = (now + self.cache_ttl_seconds, value)
        return value

    def status(self):
        manager = self.server_client.get("/")
        manager_data = manager.get("data") if isinstance(manager, dict) else {}
        if not isinstance(manager_data, dict):
            manager_data = {}

        indexer_status = None
        if self.indexer_client is not None:
            health = self.indexer_client.health()
            if isinstance(health, dict):
                indexer_status = health.get("status")

        return {
            "provider": "wazuh",
            "manager_connected": True,
            "manager_version": manager_data.get("api_version"),
            "manager_host": manager_data.get("hostname"),
            "indexer_configured": self.indexer_client is not None,
            "indexer_status": indexer_status,
        }

    def agents(self, limit=100):
        limit = max(1, min(int(limit), 500))
        return self._cached(
            f"agents:{limit}",
            lambda: [
                _normalise_agent(item)
                for item in _affected_items(
                    self.server_client.get("/agents", query={"limit": limit})
                )
                if isinstance(item, dict)
            ],
        )

    def alerts(self, limit=50):
        if self.indexer_client is None:
            raise SecurityEngineNotConfigured("Wazuh indexer is not configured")
        limit = max(1, min(int(limit), 200))

        def load():
            payload = self.indexer_client.search_alerts(limit)
            hits = payload.get("hits") if isinstance(payload, dict) else {}
            raw_hits = hits.get("hits") if isinstance(hits, dict) else []
            return [
                _normalise_alert(hit)
                for hit in raw_hits
                if isinstance(hit, dict)
            ]

        return self._cached(f"alerts:{limit}", load)

    def sca(self, agent_id, limit=100):
        limit = max(1, min(int(limit), 500))
        return self._cached(
            f"sca:{agent_id}:{limit}",
            lambda: [
                _normalise_sca(item)
                for item in _affected_items(
                    self.server_client.get(
                        f"/sca/{agent_id}", query={"limit": limit}
                    )
                )
                if isinstance(item, dict)
            ],
        )

    def fim(self, agent_id, limit=100):
        limit = max(1, min(int(limit), 500))
        return self._cached(
            f"fim:{agent_id}:{limit}",
            lambda: [
                _normalise_fim(item)
                for item in _affected_items(
                    self.server_client.get(
                        f"/syscheck/{agent_id}", query={"limit": limit}
                    )
                )
                if isinstance(item, dict)
            ],
        )

    def overview(self):
        def load():
            agents = self.agents(limit=500)
            alerts = self.alerts(limit=100) if self.indexer_client is not None else []
            active = sum(1 for agent in agents if agent.get("status") == "active")
            disconnected = sum(
                1
                for agent in agents
                if agent.get("status") in {"disconnected", "never_connected"}
            )
            critical = sum(1 for alert in alerts if alert.get("level", 0) >= 12)
            high = sum(1 for alert in alerts if 8 <= alert.get("level", 0) < 12)
            return {
                "provider": "wazuh",
                "agents": {
                    "total": len(agents),
                    "active": active,
                    "disconnected": disconnected,
                },
                "alerts": {
                    "sample_size": len(alerts),
                    "critical": critical,
                    "high": high,
                    "latest_at": alerts[0].get("timestamp") if alerts else None,
                    "available": self.indexer_client is not None,
                },
            }

        return self._cached("overview", load)
