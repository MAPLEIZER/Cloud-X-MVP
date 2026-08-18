# Self-hosted error tracking

Cloud-X uses **GlitchTip** as the reference centralized error-tracking service for Phase 1. GlitchTip is open source, MIT licensed, self-hostable, and accepts the Sentry event protocol used by the MIT-licensed `sentry-sdk` Python client.

Cloud-X does **not** require hosted Sentry or any other external telemetry SaaS. If `ERROR_TRACKING_DSN` is unset, event delivery is disabled and the application continues to run with structured local JSON logs and health probes.

## Architecture

```text
Browser runtime error
  -> local Cloud-X scrubber
  -> authenticated POST /api/client-errors
  -> Cloud-X backend scrubber
  -> Sentry-compatible DSN
  -> self-hosted GlitchTip

Flask unhandled exception
  -> Sentry Python SDK scrubber
  -> self-hosted GlitchTip

RQ scan-worker exception
  -> Sentry Python SDK RQ integration + scrubber
  -> self-hosted GlitchTip
```

The browser never receives the GlitchTip DSN. This keeps ingestion credentials and policy at the Cloud-X backend boundary and prevents a direct unauthenticated browser-to-error-service telemetry path.

## Privacy and security defaults

The integration is deliberately conservative:

- `send_default_pii` is disabled;
- request bodies are never collected;
- cookies, authorization headers and request headers are removed;
- query strings and URL fragments are removed;
- local stack-frame variables are removed;
- email, username, IP address and arbitrary user metadata are removed;
- Cloud-X user IDs are omitted unless `ERROR_TRACKING_INCLUDE_USER_ID=true` is explicitly selected;
- bearer tokens, password/secret/token/API-key shaped values and credentials embedded in URLs receive a second redaction pass;
- frontend events only accept a fixed allow-list of fields;
- tracing is disabled by default (`ERROR_TRACKING_TRACES_SAMPLE_RATE=0.0`).

Do not put customer payloads, Wazuh credentials, Clerk tokens, SSH/WinRM credentials, scan command lines containing secrets, or authentication material into manual error-tracking messages.

## Deploy GlitchTip

Use the upstream GlitchTip self-hosting documentation and its supported Docker Compose deployment rather than copying GlitchTip source into this repository. Keep the GlitchTip service on private/internal infrastructure wherever practical and put its web UI behind your normal TLS/access-control boundary.

Minimum operator flow:

1. deploy a supported GlitchTip release with its PostgreSQL database;
2. terminate TLS for the GlitchTip UI/ingestion endpoint;
3. create a dedicated Cloud-X project in GlitchTip;
4. copy that project's Sentry-compatible DSN;
5. place the DSN only in the Cloud-X backend/worker secret environment as `ERROR_TRACKING_DSN`;
6. set `ERROR_TRACKING_ENVIRONMENT` to the deployment tier (`staging`, `pilot`, `production`);
7. set `ERROR_TRACKING_RELEASE` to the immutable Cloud-X release/tag when release automation supplies one;
8. restart the API and scan-worker containers;
9. exercise one controlled backend/frontend test error and confirm it appears in the self-hosted GlitchTip project;
10. verify the received event does not contain request bodies, credentials, tokens, query strings, cookies, email addresses or IP addresses.

## Environment variables

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `ERROR_TRACKING_DSN` | No | empty | Sentry-compatible GlitchTip project DSN. Empty disables centralized delivery. |
| `ERROR_TRACKING_ENVIRONMENT` | No | `production` | Environment label attached to events. |
| `ERROR_TRACKING_RELEASE` | No | unset | Immutable Cloud-X release identifier. |
| `ERROR_TRACKING_TRACES_SAMPLE_RATE` | No | `0.0` | Performance trace sample rate from 0 to 1. Keep disabled until explicitly needed. |
| `ERROR_TRACKING_INCLUDE_USER_ID` | No | `false` | Allow the opaque Cloud-X user ID only; no email/IP/profile metadata. |

## Health semantics

Centralized error tracking is **not** a readiness dependency. A GlitchTip outage must not take the security control plane offline. Cloud-X continues to emit local structured logs and exposes:

- `/api/health/live` — process liveness;
- `/api/health/ready` — PostgreSQL + Redis/RQ readiness, with Wazuh reported as an optional degraded dependency;
- reverse-proxy `/_health/live` and `/_health/ready` — the same application probes through nginx.

The error tracker is therefore an observability sink, not a control-plane dependency.

## Upgrade policy

GlitchTip and the Sentry-compatible client SDK are third-party components. Treat upgrades like any other dependency change:

- review upstream release/security notes;
- update deliberately rather than tracking a mutable branch;
- run Cloud-X regression tests;
- verify a sanitized test event end-to-end;
- record the deployed GlitchTip and Cloud-X versions in the pilot/deployment evidence.

Cloud-X should remain compatible with the generic Sentry ingestion contract rather than taking a hard dependency on a GlitchTip-specific private API.
