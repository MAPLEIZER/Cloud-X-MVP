# Cloud-X Security

> **Status: product validation / pre-production**
>
> Cloud-X is being refocused from a broad “all-in-one SIEM” experiment into a self-hosted security operations appliance for SMBs and MSPs. The project is **not production-ready** and should not yet be relied on as a primary security control.

Cloud-X provides an opinionated control plane over open-source security components, with **Wazuh as the initial security engine**. The goal is not to rebuild Wazuh or expose every SIEM screen. Cloud-X focuses on the parts that small IT teams and MSPs still have to operationalize themselves: deployment, endpoint onboarding, customer isolation, policy abstraction, actionable findings, safe remediation workflows, notifications, evidence, reporting, and upgrades.

## Product thesis

Cloud-X should make an existing open security engine dramatically easier to deploy and operate.

```text
                         CLOUD-X
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
      Deployment         Decisions         Evidence
          │                 │                 │
   signed installers    actionable       client reports
   guided appliance      findings         compliance packs
   safe upgrades         safe fixes       audit trail
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                  SecurityEngine adapter
                            │
                       WAZUH CORE
                            │
          endpoints • events • response
                            │
                optional sensors later
```

The underlying engine is deliberately hidden behind a versioned `SecurityEngine` adapter so Cloud-X can change or add engines later without rebuilding the customer-facing product.

## What Cloud-X owns

- Guided self-hosted/private-cloud deployment
- Tenant/customer/site model for MSP workflows
- Endpoint enrolment and signed bootstrap packaging
- Opinionated security policy profiles
- A smaller actionable finding model over raw security alerts
- Typed, auditable remediation actions rather than arbitrary shell access
- Notifications and ticket/RMM integrations
- Client-ready reports and evidence packs
- Upgrade/rollback orchestration and compatibility checks
- Product-level health, audit and support telemetry

## What Cloud-X does **not** rebuild

Wazuh remains responsible for the initial implementation of endpoint telemetry, agent protocol, FIM/SCA/inventory, vulnerability data, low-level rules/detection and response primitives. Optional components such as Suricata, Zeek, Velociraptor or Greenbone are only candidates for later modules when real pilot demand justifies them.

Cloud-X is **not** intended to become another generic SIEM dashboard, a home-grown EDR engine, or a collection of unrestricted remote-execution tools.

## Repository map

| Repository | Role | Status |
|---|---|---|
| **Cloud-X-MVP** | Canonical Cloud-X product repository | **Active during validation** |
| [Cloud-X-security-agent](https://github.com/MAPLEIZER/Cloud-X-security-agent) | Historical Windows/Linux installer and Wazuh policy work | Source material to consolidate into canonical packaging |
| [Cloud-X-Dashboard](https://github.com/MAPLEIZER/Cloud-X-Dashboard) | Legacy dashboard/UI development snapshot | Source material / provenance; not canonical |

Do not implement the same installer, backend or configuration logic independently across these repositories. New product work belongs here unless the roadmap explicitly creates a separate independently versioned component.

See [`docs/REPOSITORY_MAP.md`](docs/REPOSITORY_MAP.md) for the consolidation plan.

## Current architecture

The existing codebase includes:

- React + TypeScript + Vite frontend
- Flask/Python control API
- Clerk-backed application authentication
- Nmap/Masscan/ZMap scanning integration
- Windows/Linux/macOS Wazuh installation work
- Wazuh active-response and policy configuration work
- Docker/CI packaging and security regression checks

The next architecture step is to put Wazuh behind the Cloud-X adapter and separate privileged scanner/deployment responsibilities from the ordinary web control plane.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Roadmap

Development is gated rather than open-ended. The first objective is a roughly 90-day validation cycle, not a twelve-month rewrite.

The project continues only if real MSP/SMB pilots demonstrate that Cloud-X materially reduces deployment and operating effort. The core gates include real design partners, independent deployments, unattended endpoint enrolment, measurable setup time, tenant-isolation testing and willingness to pay.

See:

- [`docs/ROADMAP.md`](docs/ROADMAP.md) — implementation and validation roadmap
- [`docs/research/2026-08-14-smb-msp-soc-product-decision.md`](docs/research/2026-08-14-smb-msp-soc-product-decision.md) — product/architecture research and go/no-go decision
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — target architecture and boundaries

## Security posture

Cloud-X is pre-production. Development builds are unsupported for protecting production environments.

The project follows several hard rules going forward:

1. No arbitrary remote command execution in the default product workflow.
2. No mutable `main`-branch scripts as a production installer channel.
3. Endpoint/bootstrap releases must be versioned and signed before production use.
4. Tenant isolation must be tested as a security boundary.
5. Security-engine credentials are tenant-scoped and isolated.
6. Build/signing credentials must not share a trust domain with customer-facing services.
7. Critical administrative actions must be auditable.

See [`SECURITY.md`](SECURITY.md).

## Development

The repository still contains historical MVP structure while the consolidation roadmap is executed. Existing development commands are retained for contributors, but they do not represent a supported production deployment.

```bash
# frontend
pnpm install
pnpm dev

# backend
cd cloudx-flask-backend
python -m venv .venv
# activate the virtual environment for your OS
pip install -r requirements.txt
```

Production packaging will move toward versioned, signed release artifacts and an opinionated appliance bootstrap rather than ad-hoc development commands.

## Licensing

Cloud-X-authored code is licensed under the [MIT License](LICENSE).

Third-party software, dependencies and adapted components remain subject to their own licenses. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Project decision gate

If the validation cycle does not demonstrate meaningful operator value and commercial pull, Cloud-X will be preserved as an archived security-engineering portfolio/reference project rather than expanded into a home-grown SIEM.
