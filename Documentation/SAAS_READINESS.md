# Cloud-X — SaaS-Readiness Audit & Roadmap

> Internal engineering planning document. Last updated: **June 2026**.
> A polished version of this report is available as [`SAAS_READINESS_AUDIT.html`](SAAS_READINESS_AUDIT.html).
> For the detailed execution timeline see [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md); for the high-level feature roadmap see [`ROADMAP.md`](ROADMAP.md).

## Verdict

Cloud-X-MVP is a **working single-tenant prototype** with a strong frontend foundation and a real, end-to-end network-scanning feature. The work that *defines* a SaaS — server-side authentication, tenant isolation, the Wazuh SIEM core, durable async execution, and billing — is still ahead of us.

**SaaS-readiness: ~18%.** The system is a functional prototype on a trusted network; authentication, tenant isolation, and hardening are in progress before any public or multi-tenant exposure.

## Status snapshot

| Capability | Status | Notes |
|---|---|---|
| Frontend shell (layout, routing, theming, Clerk sign-in) | ✅ Built | React 19 + TanStack + Tailwind 4; Clerk enforced in the UI. |
| Network scanning (nmap / zmap / masscan) | ✅ Built | End-to-end: jobs, progress, results, history. Most complete feature. |
| System monitor | 🟡 Partial | Local metrics via `psutil`; remote = ping; some placeholder values. |
| Agent deploy — Linux/macOS (SSH) | 🟡 Partial | Flow present; needs host-key handling + input hardening. |
| Agent deploy — Windows (WinRM) | ⚪ Scaffold | Stub. The standalone `Cloud-X-security-agent` installer should be the canonical path. |
| Wazuh "single pane" (core value) | ⚪ Not built | No backend connector yet; page is a placeholder. **Highest-value Phase 1 item.** |
| Advanced (scripts / SOAR) | ⚪ Not built | Placeholder. |
| Billing | ⚪ Not built | No payment integration; tiers defined on paper. |
| Servers / multi-node | ⚪ Scaffold | Browser-local node list; no server-side tenant/node model. |

## Architecture: today → target

**Today:** single Flask service · SQLite file · background scans on worker threads with in-memory state · access control client-side only · no tenant model · "nodes" tracked per-browser in `localStorage`.

**Target (SaaS):** API gateway → stateless workers → Postgres + Redis · durable job queue with state in the DB · Clerk JWT verified server-side on every request · `org_id` on every row with scoped queries + RBAC · control plane mapping tenants → Wazuh + worker nodes.

## Pre-production hardening checklist

Cloud-X is itself a security product, so its own posture is a first-class requirement. Close these before any internet-facing or multi-customer deployment (remediation-framed):

- **[P0] Authentication & authorization** — verify identity (Clerk session JWT) server-side on every API endpoint; attach the token from the client. Today access is enforced only in the frontend.
- **[P0] Harden deployment endpoints** — require auth, restrict to allow-listed hosts, treat all deployment inputs as data (strict quoting / parameterised execution); never log credentials.
- **[P0] Input validation for scans** — validate targets (IP/CIDR/hostname); build scanner command-lines as argument arrays, not strings.
- **[P0] Secrets & artifact hygiene** — remove the DB file, committed `venv/`, and certificate from version control; add `.gitignore` and `.env.example`; move config to env vars.
- **[P1] Production runtime** — serve via gunicorn as a non-root user; isolate raw-socket scanners; restrict CORS to known origins.
- **[P1] Data & async durability** — Postgres + Alembic migrations; durable job queue with state in the DB.

## Phase 1 — Harden & complete the core (~6–10 weeks, pilot-ready)

Goal: a secure, deployable single-org product to put in front of 3–5 design-partner SMBs, with the Wazuh single pane actually working.

- **A. Lock down the backend** — server-side auth on every route; input validation; deployment-endpoint hardening; restricted CORS; gunicorn + non-root container; purge secrets from git.
- **B. Make the core value real (Wazuh)** — backend Wazuh connector (agents, alerts, FIM, SCA via the Manager REST API); build the Wazuh dashboard page against it; adopt the standalone `Cloud-X-security-agent` installer as the canonical enrollment path.
- **C. Productionise (single-tenant)** — Postgres + Alembic; durable job queue; real system-monitor; structured logging, error tracking, health probes; nginx + HTTPS; in-region host.
- **D. Pilot deliverable** — monthly **security & posture report (PDF)** from scan + Wazuh + SCA data.

**Definition of done:** every API authenticated · runs non-root over HTTPS on a cloud host · Wazuh agents & alerts visible in the dashboard · onboard an endpoint in <15 min · generate a posture PDF for one pilot org.

## Phase 2 — Multi-tenant SaaS & monetisation (~8–12 weeks, self-serve)

Goal: serve multiple organisations with hard isolation, self-serve onboarding, and billing — including local payment rails.

- **A. Tenancy model** — Organisation + Membership (map to Clerk Organizations); `org_id` on every table; scoped queries; RBAC (owner/admin/analyst/viewer); replace the browser-local "servers" idea with a server-side tenant→node map behind one gateway.
- **B. Wazuh isolation strategy** — manager-per-tenant (strong isolation) for regulated/BFSI; shared manager + Wazuh RBAC & per-tenant agent groups for the SMB tier; secure node ↔ control-plane comms (mTLS / signed tokens).
- **C. Billing & plans** — Stripe subscriptions + metered per-agent usage; local rails (M-Pesa via Daraja, Paystack/Flutterwave) priced in KES; enforce Free/Basic/Pro tiers from real usage.
- **D. Compliance & trust (GTM wedge)** — Kenya DPA-aligned features (in-region residency, audit logs, data export/erasure, retention); "compliance-by-design" report templates (DPA + CIS from SCA data).

**Definition of done:** multiple isolated orgs (cross-tenant access provably impossible) · per-org Wazuh data · per-org billing incl. M-Pesa · admins manage org/members/plan · audit log + data export.

## Deferred (Phase 3+)

NIDS/IDPS · DLP · EUBA · SOAR auto-response · VirusTotal/Shodan integrations · **★ AI alert triage + plain-English/Swahili summaries** (the natural differentiator — slot "explain this alert & recommend an action" as the first Phase 3 feature, once real Wazuh data is flowing).

---

*Estimates assume 1–2 focused engineers and exclude SOC/analyst staffing, which a managed-security service eventually requires.*
