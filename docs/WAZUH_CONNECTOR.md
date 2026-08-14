# Wazuh SecurityEngine connector

Status: Phase 1 implementation for issue #24.

Cloud-X uses Wazuh behind the provider-neutral `SecurityEngine` contract defined in `cloudx-flask-backend/security_engine/base.py`. Product code and the browser consume normalized Cloud-X objects rather than Wazuh server/indexer response shapes.

## Upstream split

The connector deliberately uses two Wazuh APIs:

1. **Wazuh server API** (`WAZUH_API_URL`, normally HTTPS/55000)
   - JWT authentication obtained from `POST /security/user/authenticate?raw=true` using dedicated API credentials.
   - Agent inventory from `GET /agents`.
   - SCA policy results from `GET /sca/{agent_id}`.
   - File Integrity Monitoring state from `GET /syscheck/{agent_id}`.
2. **Wazuh Indexer API** (`WAZUH_INDEXER_URL`, normally HTTPS/9200)
   - Separate least-privilege Indexer credentials.
   - Alert documents queried from `wazuh-alerts*`.

This split avoids pretending alert documents are a Wazuh Manager REST resource and keeps Indexer access entirely server-side.

## Security defaults

- Upstream URLs must use HTTPS.
- TLS certificate verification defaults to `true` for Manager and Indexer independently.
- Private CAs can be supplied with `WAZUH_API_CA_BUNDLE` and `WAZUH_INDEXER_CA_BUNDLE`.
- `*_VERIFY_TLS=false` is an explicit operator opt-out for isolated validation only; supported deployments should install/trust the correct CA instead.
- Credentials and Manager JWTs never leave the backend and are not logged by the adapter.
- Wazuh Manager JWTs are cached in memory and refreshed once when the server returns HTTP 401.
- Responses are size-bounded and API list limits are bounded by Cloud-X routes.
- Normalized results are cached briefly (`WAZUH_CACHE_TTL_SECONDS`, default 15 seconds) to avoid polling Wazuh on every browser render.
- Partial Manager-only configuration is supported for agent/SCA/FIM validation. Alerts return a controlled 503 until the Indexer is configured.
- Partial credential triplets fail backend startup rather than silently disabling TLS/authentication.

## Environment

```env
WAZUH_API_URL=https://wazuh-manager.example.com:55000
WAZUH_API_USERNAME=cloudx-api
WAZUH_API_PASSWORD=replace_me
WAZUH_API_VERIFY_TLS=true
# WAZUH_API_CA_BUNDLE=/run/secrets/wazuh-manager-ca.crt

WAZUH_INDEXER_URL=https://wazuh-indexer.example.com:9200
WAZUH_INDEXER_USERNAME=cloudx-indexer
WAZUH_INDEXER_PASSWORD=replace_me
WAZUH_INDEXER_VERIFY_TLS=true
# WAZUH_INDEXER_CA_BUNDLE=/run/secrets/wazuh-indexer-ca.crt

WAZUH_REQUEST_TIMEOUT_SECONDS=10
WAZUH_CACHE_TTL_SECONDS=15
```

Use dedicated least-privilege accounts. Do not reuse Wazuh dashboard/admin credentials in a production Cloud-X deployment.

## Cloud-X API contract

All routes below require the existing Clerk backend authorization:

| Route | Cloud-X normalized purpose |
|---|---|
| `GET /api/security/status` | Manager/Indexer connection status and provider metadata |
| `GET /api/security/overview` | Bounded agent/alert posture summary |
| `GET /api/security/agents?limit=100` | Endpoint inventory and connection state |
| `GET /api/security/alerts?limit=50` | Recent normalized alerts from `wazuh-alerts*` |
| `GET /api/security/sca?agent_id=001` | SCA policy summaries for one endpoint |
| `GET /api/security/fim?agent_id=001` | FIM file state for one endpoint |

Cloud-X returns 503 when the provider/capability is not configured, 502 when the configured upstream cannot satisfy a request, and 400 for invalid local parameters. Upstream exception bodies are not forwarded to the browser.

## Normalization boundary

Examples of Cloud-X-owned fields:

- agents: `id`, `name`, `status`, `ip`, `groups`, `version`, `node`, `last_seen`, normalized OS fields;
- alerts: `id`, `timestamp`, `level`, `rule_id`, `description`, `groups`, `mitre_ids`, normalized agent identity, manager and location;
- SCA: policy ID/name, passed/failed/invalid/total counts, score and last scan;
- FIM: path/type/size/permissions/owner/group/hash/change count/timestamps.

If the Wazuh API changes, only the adapter and its contract tests should need compatibility work; the Cloud-X UI should not be rewritten around Wazuh response envelopes.

## Agent enrollment source of truth

The standalone `cloudx-security-agent/` package is the canonical Cloud-X agent/enrollment surface for pilots. Its Wazuh configuration and cross-platform installer assets should be treated as the source of truth for endpoint onboarding. The copies under `cloudx-flask-backend/scripts/` exist for the older remote-deployment compatibility path and must not evolve into a second independent agent product.

As Phase 1 continues, prefer installation/enrollment flows that consume the standalone package and Wazuh enrollment primitives rather than adding more endpoint logic to the Flask service.

## Validation boundary

Unit/contract tests can prove authentication flow, normalization, caching, route behavior, TLS/config fail-closed behavior and representative Wazuh response handling. Issue #24 should only be considered fully operationally validated after Cloud-X is connected to a real Wazuh Manager + Indexer and the dashboard shows real agents plus real alert/SCA/FIM data from a pilot endpoint.
