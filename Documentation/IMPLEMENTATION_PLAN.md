# Cloud-X: Detailed Implementation Plan (MVP to AI-Powered SOC)

Last updated: 2025-12-16  
Scope: Implements the planned roadmap items in `Documentation/ROADMAP.md` and extends the future vision into an AI-assisted SOC with case management + SOAR-style playbooks.

---

## 0) Executive Summary (What we're building)

Cloud-X evolves from a network scanning MVP into a multi-tenant security platform for SMBs with:

1. **Core platform foundation**: authentication, multi-tenant RBAC, audit logs, config management, and a real database.
2. **Short-term planned modules (ROADMAP.md)**:
   - **Downloads App**: secure artifact/report repository + RBAC + PDF/CSV/JSON exports.
   - **Wazuh Integration App**: agent inventory, alerts view, compliance (SCA), and FIM results.
   - **Advanced Tools App**: safe script/playbook execution, JSON/config editor, and external API integrations manager.
   - **Billing**: Stripe subscriptions and usage-based gating.
3. **Future modules (ROADMAP.md)**: NIDS/IDPS, DLP, EUBA.
4. **AI-powered SOC**: unified event ingestion, correlation, incident/case workflow, AI-assisted triage + summarization, and guided response (human-in-the-loop).

The plan is written to be executed incrementally without breaking existing functionality (network scans + dashboard).

---

## 1) Current State Snapshot (Repo reality check)

### Frontend (Vite + React + TS + TanStack Router)
- Implemented: `/apps/network/scan`, `/apps/network/history`, `/dashboard`, `/settings`.
- Placeholders (`ComingSoon`): `/apps/downloads`, `/apps/wazuh`, `/apps/advanced`, `/billing`, `/documentation`.
- Partial/placeholder: `/servers` route exists but is not implemented.
- Auth: Clerk is wired at the root route; protected routes use `ProtectedRoute` + redirect to `/sign-in`.

### Backend (Flask)
- Implemented:
  - Scans: `POST /api/scans`, `GET /api/scans`, `GET /api/scans/<job_id>`, stop/delete.
  - System monitor: `GET /api/system-monitor?target=...` (local psutil, remote ping fallback).
  - Agent deployment: `POST /api/deploy/agent` (WinRM/SSH; simplified).
  - Node deploy: `POST /api/deploy/node` (placeholder demo).
- Limitations to address:
  - No authentication/authorization.
  - SQLite only.
- Threading-based "async"; no durable queue.
  - No structured domain model for tenants/orgs, files, billing, Wazuh assets, incidents.

---

## 2) Target Product Requirements (from ROADMAP.md)

### Downloads App (Short term)
- Secure storage for tools/reports.
- RBAC enforcement.
- Report generation: PDF/CSV/JSON exports.

### Wazuh Integration App (Short term)
- Agent dashboard.
- Alerts view (real-time-ish).
- Policy compliance (SCA).
- File Integrity Monitoring (FIM) results.

### Advanced Tools App (Short term)
- Script executor (approved automation).
- JSON editor (configs, rules).
- API manager (VirusTotal, Shodan, Slack, etc).

### Billing (Short term)
- Stripe integration.
- Subscription tiers (Free/Basic/Pro) + usage gating.

### Future Vision modules (Longer term)
- NIDS/IDPS.
- DLP.
- EUBA.
- AI & Analytics (SOAR, threat hunting, correlation).

---

## 3) Architecture Blueprint (Decisions + why)

### 3.1 Multi-tenant + RBAC (non-negotiable foundation)

**Goal:** Every object belongs to a tenant (Clerk Organization). Every request is authorized server-side.

- **Identity provider:** Clerk (already present in UI).
- **Tenant primitive:** Clerk Organization ID (e.g., `org_...`).
- **Roles/permissions:**
  - Start simple with org roles: `owner`, `admin`, `analyst`, `viewer`.
  - Expand later with permissions/feature flags as needed.
- **Backend auth method:**
  - Frontend sends Clerk JWT (from `getToken()`).
  - Backend verifies JWT using Clerk JWKS (cache keys) and extracts:
    - `sub` (user id),
    - `org_id` (active org),
    - role claims (if used).

**Deliverable:** A Flask auth middleware that yields `(tenant_id, user_id, roles)` for every request; all DB queries must be tenant-scoped.

### 3.2 Data store: SQLite to Postgres (and migrations)

**Why:** Multi-tenant data, reporting, billing, incidents, and event retention quickly outgrow SQLite. Also enables pgvector for AI later.

- Adopt **PostgreSQL** as the primary DB.
- Add **Alembic** for migrations.
- Keep SQLite as a "dev fallback" only if necessary.

### 3.3 Background jobs: Threads to durable queue (Celery + Redis)

**Why:** Scans, report generation, file scanning, Wazuh polling, and AI enrichment need retry, scheduling, and durability.

- Use **Celery** workers for:
  - network scans,
  - report generation,
  - file processing (hashing/AV scan),
  - periodic Wazuh sync,
  - alert correlation/AI jobs.
- Use **Redis** as broker/result backend (or RabbitMQ later).

### 3.4 Wazuh Integration: Manager API + Indexer access

**Reality:** The Wazuh Manager API is great for agent inventory, SCA, syscheck/FIM, and active response. "Alerts stream" commonly comes from the Wazuh Indexer (OpenSearch).

Plan supports both:
- **Wazuh Manager API (HTTP):**
  - Auth: `POST /security/user/authenticate` (basic auth) -> returns JWT token -> subsequent requests with `Authorization: Bearer <token>`.
  - Useful endpoints:
    - `GET /agents`, `GET /agents/summary`, `GET /agents/{agent_id}/...`
    - `GET /sca/{agent_id}`, `GET /sca/{agent_id}/checks/{policy_id}`
    - `GET /syscheck/{agent_id}`
    - `PUT /active-response` (run active response commands)
- **Wazuh Indexer / OpenSearch (HTTP):**
  - Query indices for alerts/events for real-time-ish feeds and analytics.
  - Implement a small query layer and strict allowlist of query parameters.

### 3.5 Secure file handling (Downloads App)

Follow secure upload guidance:
- Allowlist file types; enforce max size; store outside web root.
- Virus scan (optional MVP, recommended production).
- Hash everything (sha256) + immutable content addressing.
- RBAC enforced at download time; generate short-lived download URLs.
- Always log uploads/downloads for audit.

### 3.6 Billing: Stripe + entitlements

Billing is an authorization system in disguise.

- Stripe Checkout for subscriptions (fastest path) + Customer Portal.
- Webhook-driven state:
  - subscription created/updated/canceled,
  - invoice paid/failed.
- Store entitlements per tenant:
  - max agents,
  - scan concurrency,
  - retention days,
  - enabled modules (Downloads/Wazuh/Advanced).

### 3.7 AI SOC (North-star)

AI isn't a feature; it's a system layered over clean data + workflows:

- **Unified event model**: everything becomes an "event" (scan finding, Wazuh alert, NIDS alert, DLP alert, user action).
- **Correlation + cases**:
  - rule-based correlation first,
  - then ML/AI enrichment.
- **AI assistant (human-in-the-loop)**:
  - summarize incidents,
  - group related events,
  - propose next steps,
  - generate safe remediation playbooks (approval required).
- **Knowledge base / RAG**:
  - store internal runbooks, docs, policies,
  - retrieve relevant context for suggestions.
- **Guardrails**:
  - no autonomous destructive actions,
  - redact secrets,
  - log all AI outputs and user approvals.

---

## 4) Data Model (Proposed tables)

Minimum viable schema to unblock all roadmap modules:

### Tenant + auth
- `tenants` (id=clerk_org_id, name, created_at)
- `users` (id=clerk_user_id, email, display_name, created_at)
- `tenant_memberships` (tenant_id, user_id, role, created_at)
- `audit_log` (tenant_id, actor_user_id, action, target_type, target_id, metadata_json, created_at, ip, user_agent)

### Scans
- `scans` (id, tenant_id, created_by_user_id, tool, target, scan_type, status, progress, started_at, finished_at)
- `scan_results` (scan_id, raw_json, normalized_json, severity_summary, created_at)

### Downloads (files + reports)
- `files` (id, tenant_id, uploaded_by_user_id, name, content_type, size_bytes, sha256, storage_key, status, created_at)
- `file_tags` (file_id, tag)
- `file_permissions` (file_id, role, can_read, can_write) OR use role-based policy.
- `reports` (id, tenant_id, type, params_json, status, storage_key, created_at)

### Wazuh integration
- `wazuh_connections` (tenant_id, manager_url, indexer_url, auth_type, secret_ref, created_at, updated_at)
- `wazuh_agents_cache` (tenant_id, agent_id, data_json, last_sync_at)
- `wazuh_alerts_cache` (tenant_id, cursor, last_sync_at) (optional; depends on indexer query strategy)

### Advanced tools (playbooks + integrations)
- `integrations` (tenant_id, provider, name, config_json, secret_ref, created_at)
- `playbooks` (tenant_id, name, description, steps_json, created_at, updated_at, enabled)
- `playbook_runs` (tenant_id, playbook_id, requested_by_user_id, target_json, status, logs_json, created_at, finished_at)

### Billing
- `billing_customers` (tenant_id, stripe_customer_id, created_at)
- `subscriptions` (tenant_id, stripe_subscription_id, status, current_period_end, plan, metadata_json)
- `entitlements` (tenant_id, max_agents, max_scans_per_day, retention_days, features_json)

### SOC (future)
- `events` (tenant_id, source, source_id, event_type, severity, payload_json, ts)
- `detections` (tenant_id, rule_id, event_ids, score, status, created_at)
- `cases` (tenant_id, title, status, severity, owner_user_id, summary, created_at, updated_at)
- `case_events` (case_id, event_id)
- `case_comments` (case_id, user_id, comment, created_at)
- `ai_enrichments` (tenant_id, object_type, object_id, model, prompt_hash, output_json, created_at)

---

## 5) API Design (Planned endpoints)

### 5.1 Foundation (auth + tenant)
- `GET /api/me` -> user + tenant context
- `GET /api/entitlements` -> module gating
- `GET /api/audit` -> audit log list (admin only)

### 5.2 Scans (upgrade existing)
- Keep existing endpoints but add:
  - tenant scoping,
  - created_by,
  - normalized results,
  - pagination + filtering.
- Add:
  - `GET /api/scans/:id/export?format=csv|json|pdf`
  - `POST /api/scans/:id/report` (async report generation)

### 5.3 Downloads
- `POST /api/files` (upload; multipart or signed URL flow)
- `GET /api/files` (list; filter by tag/type/date)
- `GET /api/files/:id` (metadata)
- `GET /api/files/:id/download` (stream or signed URL)
- `DELETE /api/files/:id` (admin)

### 5.4 Wazuh
- `POST /api/wazuh/connect` (store connection, validate credentials)
- `GET /api/wazuh/agents`
- `GET /api/wazuh/agents/:id`
- `GET /api/wazuh/agents/:id/sca`
- `GET /api/wazuh/agents/:id/sca/:policy_id/checks`
- `GET /api/wazuh/agents/:id/fim` (syscheck)
- `GET /api/wazuh/alerts` (via indexer; filters)
- `POST /api/wazuh/active-response` (restricted; admin/analyst)

### 5.5 Advanced tools
- `GET/POST /api/playbooks`
- `POST /api/playbooks/:id/run`
- `GET /api/playbook-runs/:id`
- `GET/POST /api/integrations`

### 5.6 Billing
- `POST /api/billing/checkout-session`
- `POST /api/billing/portal-session`
- `POST /api/billing/webhook` (Stripe)

### 5.7 SOC (future)
- `GET /api/events` (filter/search)
- `GET/POST /api/cases`
- `POST /api/cases/:id/assign`
- `POST /api/ai/summarize` (case summary)
- `POST /api/ai/recommend` (next steps / playbook suggestions)

---

## 6) UI/UX Plan (Routes + screens)

### Downloads (`/_protected/apps/downloads`)
Screens:
- Library list (filters: tag/type/date; sorting; bulk select).
- Upload modal (drag/drop; validation; progress; classification/tags).
- File detail (hash, version, permissions, audit trail).
- Reports section (generated exports; retention).

### Wazuh (`/_protected/apps/wazuh`)
Screens:
- Agent inventory (status, version, OS, last keepalive, groups).
- Agent detail:
  - alerts timeline,
  - SCA score and checks,
  - FIM changes list,
  - actions (restart agent, active response) with approvals.

### Advanced (`/_protected/apps/advanced`)
Screens:
- Playbooks (create/edit/enable/disable; versioning).
- Run history with logs.
- JSON/config editor with schema validation (for Wazuh configs + internal configs).
- Integrations manager (VirusTotal/Shodan/Slack/etc) with secret handling UI.

### Billing (`/_protected/billing`)
Screens:
- Current plan, limits, usage.
- Upgrade/downgrade via Stripe checkout.
- Payment method management via Stripe portal.

### Servers (`/_protected/servers`)
Screens:
- List nodes (URL, status, last seen, roles/capabilities).
- Add node + validation.
- Optional: "deploy node" wizard (advanced; admin-only).

### Documentation (`/_protected/documentation`)
Screens:
- Markdown-based docs viewer (project docs + runbooks + KB).
- Search across docs + detections + cases (later).

---

## 7) Implementation Timeline (Execution-ready)

This timeline assumes 1-2 devs. If you have more, parallelize by workstream.

### Phase 0 (Week 0): Baseline + Guardrails
Deliverables:
- Confirm environments + secrets strategy.
- Decide on: Postgres hosting (local Docker vs managed), Redis hosting, storage backend (local vs S3/MinIO).

Execution steps:
1. Add `.env.example` for backend (DB URL, Redis, storage, Clerk, Wazuh, Stripe).
2. Add Docker Compose for local infra (postgres, redis, optional minio).
3. Ensure `.gitignore` excludes `cloudx-flask-backend/venv/` and other generated artifacts.

Acceptance criteria:
- One-command local infra boot (`docker compose up -d`) and backend can connect.

### Phase 1 (Weeks 1-2): Auth + Multi-tenant RBAC + Audit Logs
Deliverables:
- Backend auth middleware verifying Clerk JWT + tenant context.
- Tenant-scoped data access patterns in all endpoints.
- Audit logging for high-risk actions (uploads, deletes, playbook runs, billing actions).

Execution steps:
1. Backend: Implement JWT verification + request context (`tenant_id`, `user_id`, `roles`).
2. DB: Create `tenants/users/tenant_memberships/audit_log`.
3. Frontend: Add organization-aware UI state (active org, role).
4. Add entitlements endpoint stub (returns Free plan for now).

Acceptance criteria:
- Unauthenticated requests to protected endpoints return 401.
- Authenticated user cannot see another tenant's scans/files.

### Phase 2 (Weeks 2-4): Postgres migration + durable jobs
Deliverables:
- Postgres primary DB, migrations, and Celery worker.
- Scans run as Celery jobs; progress stored in DB; recoverable after restart.

Execution steps:
1. Add Alembic; migrate existing `Scan` model into `scans/scan_results` schema.
2. Introduce Celery + Redis; refactor scan runner into tasks.
3. Add pagination + filters to scan history endpoints.
4. Normalize scan output (tool-agnostic "findings" array).

Acceptance criteria:
- Restarting backend does not orphan scans; statuses recover.
- UI remains functional (scan + history + dashboard).

### Phase 3 (Weeks 4-6): Downloads App (storage + RBAC + exports)
Deliverables:
- File repository with secure upload/download.
- CSV/JSON export for scan history + at least one PDF report type.

Execution steps:
1. Implement storage abstraction:
   - `LocalStorage` (MVP) + `S3Storage` (optional).
2. Implement file upload API:
   - validate size/type,
   - compute sha256,
   - store metadata + audit logs.
3. Build Downloads UI (list + upload + download + tags).
4. Reports:
   - `scan_report` generation job -> PDF/CSV/JSON.

Acceptance criteria:
- Viewer role can download allowed files, cannot delete.
- All downloads are audited.

### Phase 4 (Weeks 6-9): Wazuh App (agents, SCA, FIM, alerts)
Deliverables:
- Wazuh connection setup per tenant.
- Agent dashboard + detail views.
- Alerts feed (indexer-backed) with filters.

Execution steps:
1. Backend: Wazuh connector module:
   - token caching/refresh,
   - strict timeouts + retries,
   - per-tenant config.
2. Implement endpoints:
   - `/api/wazuh/agents`, `/api/wazuh/agents/:id`,
   - `/api/wazuh/agents/:id/sca`,
   - `/api/wazuh/agents/:id/fim`.
3. Alerts:
   - If indexer available: implement OpenSearch query endpoint with parameter allowlist.
   - Else: provide "limited mode" (no alerts) until indexer configured.
4. Frontend: Wazuh UI screens + error states + empty states.

Acceptance criteria:
- Connect/disconnect Wazuh per tenant without impacting other tenants.
- SCA + FIM render for a chosen agent.

### Phase 5 (Weeks 9-12): Advanced Tools (Playbooks + JSON editor + integrations)
Deliverables:
- Playbooks CRUD + run history.
- Script executor using Wazuh Active Response (restricted + approval UI).
- JSON editor with schema validation (start with `ossec.conf` or scan configs).
- Integrations manager (store secrets securely).

Execution steps:
1. Define playbook schema (steps, parameters, approvals, rollback notes).
2. Implement Wazuh Active Response runner:
   - `PUT /active-response` wrapper,
   - allowlist commands,
   - per-role permissions.
3. JSON editor:
   - validate JSON against schemas,
   - version configs and allow diff/rollback.
4. Integrations:
   - define providers (VirusTotal/Shodan/Slack),
   - store secrets using env-backed encryption at rest (or external secret manager later).

Acceptance criteria:
- Playbook execution requires explicit confirmation and is audited.
- JSON editor prevents invalid config saves.

### Phase 6 (Weeks 12-14): Billing (Stripe) + Entitlements gating
Deliverables:
- Stripe subscription flows.
- Webhook processing.
- Entitlements enforced in backend and reflected in UI.

Execution steps:
1. Define plans (Free/Basic/Pro) and limits.
2. Implement checkout session + portal session endpoints.
3. Implement webhook handler:
   - verify signature,
   - update subscription + entitlements.
4. Enforce limits:
   - block advanced features if not entitled,
   - rate-limit scans,
   - cap downloads storage.
5. Billing UI page.

Acceptance criteria:
- Upgrading a plan unlocks module access without redeploy.
- Webhook signature verification is required.

### Phase 7 (Weeks 14-18): Servers + multi-node + reliability
Deliverables:
- Real servers UI and backend model for nodes.
- Node deployment endpoint upgraded from "demo" to a real Docker-based backend node bootstrap (optional).
- Observability (structured logs, basic metrics).

Execution steps:
1. Implement `servers` table + CRUD endpoints (admin only).
2. Update frontend `/servers` page to manage nodes.
3. Implement capability probing per node.
4. Optional: upgrade `/api/deploy/node` to deploy a real Cloud-X backend container + worker.

Acceptance criteria:
- Nodes can be added/removed; health shown; no tenant data leaks.

### Phase 8 (Months 5-9): Future modules (NIDS/IDPS, DLP, EUBA)

This phase is intentionally modular: each module should be shippable independently.

#### NIDS/IDPS
Recommended approach:
- Start with **Suricata** (IDS) sensors producing EVE JSON.
- Ship EVE logs into Wazuh/OpenSearch (or Cloud-X event store) for unified viewing.

Deliverables:
- Sensor onboarding + status.
- Alert feed + correlation with host/agent and scan results.

#### DLP
Pragmatic MVP:
- Start with **policy + detection**, not prevention:
  - detect sensitive data patterns in uploads/downloads and endpoint telemetry,
  - generate alerts/cases.

Deliverables:
- DLP rules library (regex + file type scope).
- DLP findings dashboard + case creation.

#### EUBA
MVP:
- Baseline user + host behavior from Wazuh logs:
  - login anomalies,
  - unusual process execution,
  - rare geo/IP.

Deliverables:
- Feature extraction jobs.
- Anomaly scoring + "why" explanations.

### Phase 9 (Months 6-12): AI-Powered SOC (Cases + AI assistant + SOAR)

Deliverables:
- **Case management**: create/assign/resolve incidents; timeline of linked events.
- **Correlation engine**: rule-based first; later learned correlation.
- **AI assistant**:
  - summarizes cases,
  - proposes next steps,
  - drafts playbooks and analyst notes,
  - answers questions grounded in internal KB (RAG).

Execution steps (sequenced to reduce risk):
1. Build SOC data plane:
   - central `events` table,
   - ingestion adapters (scans, Wazuh alerts, NIDS, DLP).
2. Build case management UI + API.
3. Implement correlation rules:
   - simple heuristics (same agent, same rule id, time window),
   - risk scoring model.
4. Add knowledge base:
   - Markdown runbooks + detection docs,
   - full-text search (Postgres) + optional vector search (pgvector).
5. Introduce AI enrichment:
   - summarize case,
   - extract IOCs,
   - recommend containment/remediation steps.
6. Add SOAR:
   - human-approved playbooks,
   - integrations (Slack/email/ticketing),
   - rollback/verification steps.

Acceptance criteria:
- Every AI output is logged, explainable, and requires user action to execute.
- SOC workflow improves analyst time-to-triage measurably (define KPIs).

---

## 8) Cross-cutting Engineering Checklist (apply in every phase)

### Security
- Enforce tenant scoping on every query.
- Validate all inputs (zod on frontend; schema validation on backend).
- Rate-limit sensitive endpoints (uploads, scans, webhooks).
- Store secrets encrypted at rest (min viable: env key + DB encryption; better: secret manager).
- Maintain audit logs for: auth, uploads, downloads, playbook runs, billing actions.

### Reliability
- Timeouts + retries for all outbound calls (Wazuh, Indexer, Stripe, integrations).
- Idempotency keys for Stripe + long-running operations.
- Background jobs must be retry-safe and resumable.

### Developer Experience
- One-command dev stack (compose).
- Clear env docs + example configs.
- Add minimal tests around auth, RBAC, and billing webhook verification.

---

## 9) Research Notes & References (quick links)

### Wazuh API
- API reference (ReDoc): https://documentation.wazuh.com/current/user-manual/api/reference.html
- OpenAPI spec (YAML): https://documentation.wazuh.com/current/_static/server-api-spec/spec-v4.14.1.yaml
- Key endpoints (from spec):
  - Auth token: `POST /security/user/authenticate` (basic auth)
  - Agents: `GET /agents`, `GET /agents/summary`
  - SCA: `GET /sca/{agent_id}`, `GET /sca/{agent_id}/checks/{policy_id}`
  - FIM: `GET /syscheck/{agent_id}`
  - Active response: `PUT /active-response`

### Stripe billing
- Subscription overview: https://stripe.com/docs/billing/subscriptions/overview
- Webhooks (general): https://stripe.com/docs/webhooks

### Clerk (multi-tenant)
- Organizations overview: https://clerk.com/docs/organizations/overview

### Secure file uploads
- OWASP File Upload Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/File_Upload_Cheat_Sheet.html

---

## 10) Open Questions (Answer early to avoid rework)

1. **Tenant model:** Is Cloud-X strictly "one organization = one customer", or do we need sub-tenants/projects?
2. **Alerts source:** Do you already have Wazuh Indexer/OpenSearch accessible, or do we need to stand it up?
3. **Storage:** Local disk vs S3/MinIO; retention requirements; encryption requirements.
4. **Billing metric:** per-agent, per-scan, per-alert, or per-seat? (This defines entitlements.)
5. **AI constraints:** where can AI run (cloud vs local), acceptable data sharing, retention, and auditing requirements.
