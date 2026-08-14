# Cloud-X SMB/MSP SOC Appliance — Product Decision Research

**Research date:** 14 August 2026  
**Decision:** Conditional GO on a Wazuh-backed orchestration product, with a mandatory archive fallback if the validation gate fails.

## Executive decision

Cloud-X should **not** attempt to become another generic SIEM/XDR dashboard and should **not** replace Wazuh with a home-grown stack of lower-level primitives before product-market fit is established.

The strongest product thesis is narrower:

> **Cloud-X is a self-hosted, MSP-first security appliance that turns Wazuh and optional security sensors into a guided multi-tenant service: deploy quickly, enrol endpoints through trusted packages, surface only actionable findings, automate safe configuration, and produce client-ready evidence without requiring a full SOC team.**

The alternative architecture — osquery/OpenSearch plus custom fleet management, rule/detection infrastructure, vulnerability correlation and response — is technically possible but shifts years of commodity security-platform engineering into Cloud-X. That work does not validate the part customers might actually pay for: easier operation.

Therefore:

- **Option A — replace Wazuh with primitives:** NO-GO for the initial product.
- **Option B — Wazuh as integration core behind a Cloud-X adapter:** CONDITIONAL GO.
- **Option C — preserve as portfolio/reference project:** mandatory fallback if the 90-day pilot gate fails.

## Why the old positioning is weak

The original Cloud-X MVP described an enterprise-style SMB security platform combining a dashboard, network scanning, Wazuh agents, alerts and future NIDS/DLP/AI features.

That scope overlaps heavily with mature free/open-source projects. Wazuh already provides endpoint agents, FIM, security configuration assessment, vulnerability detection, inventory, rules, alerts, dashboards, RBAC and active response. Security Onion combines mature network-monitoring components and SOC workflows. Velociraptor provides powerful DFIR/endpoint investigation. Greenbone provides vulnerability-management capabilities.

A prettier dashboard over those features is not enough differentiation.

The defensible layer is **operational productization**:

- reliable low-touch deployment;
- MSP customer/site workflows;
- strong isolation;
- signed/managed endpoint onboarding;
- opinionated policy packs;
- a smaller actionable finding model;
- safe remediation;
- evidence and reporting;
- predictable self-hosted/private-cloud operation;
- local/regional compliance content where demand proves value.

## Why Wazuh remains the rational initial engine

The selection criterion should not be “which dependency is least like a finished product?” It should be:

> Which component lets Cloud-X spend the least engineering effort on commodity security plumbing while preserving enough control to build a differentiated operator experience?

Wazuh currently wins because it already provides:

- secure endpoint agent architecture and lifecycle;
- centrally managed configuration and groups;
- endpoint inventory;
- FIM/SCA;
- vulnerability data;
- detection/rule content;
- active-response primitives;
- API-accessible fleet and manager operations;
- a mature fallback/admin dashboard.

Cloud-X can integrate through a versioned adapter instead of coupling customer-facing workflows directly to Wazuh internals.

### Engine escape hatch

Define a Cloud-X-owned interface:

```text
SecurityEngine
├── list_endpoints()
├── enrolment_profile()
├── apply_policy()
├── list_findings()
├── acknowledge_finding()
├── endpoint_inventory()
├── endpoint_vulnerabilities()
├── execute_approved_response()
├── health()
└── capabilities()
```

The first implementation is `WazuhSecurityEngine`. A future engine can be added only if real product constraints justify it.

## Alternatives assessed

### osquery + OpenSearch

This is the most credible “build from primitives” route. osquery is a strong cross-platform endpoint instrumentation primitive and OpenSearch is a permissively licensed search/analytics substrate.

However, Cloud-X would then need to own secure enrolment, fleet lifecycle, policy distribution, ingestion schemas, security content, correlation, FIM semantics, vulnerability correlation, response, RBAC, upgrade compatibility and much more. The result is cleaner architectural ownership but much higher maintenance/security burden.

**Decision:** valuable components, poor replacement for Wazuh before product-market fit.

### Suricata

A mature NIDS/NSM engine with structured EVE JSON output. It is a good optional passive network-sensor module once the core MSP experience works.

**Decision:** recommended later, not MVP core.

### Zeek

Excellent passive protocol/network metadata and investigation context. It adds storage and operational complexity.

**Decision:** add only after Suricata and only when pilot demand proves the investigative value.

### Velociraptor

Very capable cross-platform DFIR and threat-hunting platform. Its endpoint power also creates a high-value control plane that must be secured carefully.

**Decision:** optional later DFIR integration; do not duplicate it as a permanent second endpoint agent in the MVP.

### Greenbone/OpenVAS/GVM

Mature vulnerability-scanning stack with useful management/API surfaces.

**Decision:** optional later scanner integration, not Cloud-X core.

### Security Onion / Graylog / Elastic-centric alternatives

These replace Wazuh with another substantial product/platform while adding operational and/or licensing complexity. They do not improve Cloud-X's core differentiation enough to justify a reset.

**Decision:** do not use as the default core.

## Approximate engineering trade-off

Replacing Wazuh with primitives would require Cloud-X to recreate enough production security-platform machinery to become trustworthy. The research estimated roughly **34–54 engineering person-months** before accounting for normal product/UI work.

Indicative categories:

| Capability Cloud-X would have to own | Estimate |
|---|---:|
| Secure enrolment, fleet lifecycle, updates | 5–8 PM |
| Ingestion, normalization, schema and search pipeline | 4–7 PM |
| Detection/rule engine and content | 6–10 PM |
| Inventory and vulnerability correlation | 4–6 PM |
| Safe remote response/remediation | 4–6 PM |
| RBAC and tenant isolation | 3–5 PM |
| Backup, upgrade, rollback and packaging | 4–6 PM |
| Security assurance and automated QA | 4–6 PM |

These are planning estimates, not vendor quotes. Their purpose is to compare opportunity cost, not predict a fixed delivery date.

## Product wedge

Cloud-X only deserves continued investment if it proves a combination of differentiators that existing products do not already solve adequately for the target customer:

1. **Self-hosting/data sovereignty** — security telemetry can remain in the customer/MSP-controlled environment.
2. **Opinionated low-operations UX** — operators see problems and actions, not SIEM internals first.
3. **MSP workflows** — customer/site lifecycle, isolation, reporting and policy at the product layer.
4. **Predictable economics** — avoid making raw ingestion volume the primary product value/price axis.
5. **RMM/MDM-first endpoint deployment** — Cloud-X generates trusted unattended packages instead of becoming another remote administration tool.
6. **Evidence/compliance content** — local or industry packs only where customers validate the demand.

Kenyan/East African compliance or data-sovereignty positioning may become useful, but it must be validated with real MSPs, auditors and SMB operators rather than assumed to be a moat.

## Architecture decision

Prefer an isolated security data plane per customer during early commercial validation:

```text
MSP/SMB admin
     │
Cloud-X UI/API ─── tenant registry / audit / reports
     │
     ├── Customer A → Wazuh data plane → endpoints
     ├── Customer B → Wazuh data plane → endpoints
     └── Customer C → Wazuh data plane → endpoints
```

Do not treat dashboard tenancy alone as the whole customer security boundary. Shared-cluster optimization can be reconsidered only after explicit tenant-isolation threat modeling and tests.

## Endpoint deployment decision

Cloud-X's installer work is one of the stronger reusable assets, but the product should change how installers are delivered.

### Windows

Preserve signature verification of the upstream Wazuh MSI. Move toward a Cloud-X-signed, versioned bootstrap package with a short-lived enrolment token and standard unattended properties suitable for Intune/RMM/GPO delivery.

### Linux

Use a versioned DEB/RPM bootstrap or equivalent controlled package flow. Use repository-specific signed keyrings rather than deprecated global key installation patterns. Avoid fragile XML editing through shell substitution where supported upstream configuration mechanisms exist.

### macOS

Complete the platform only as a signed/notarized package with upstream package verification and explicit handling of macOS privacy permissions. Do not treat an unsigned root installer script as production packaging.

### Remote execution

SSH/WinRM must not be the ordinary onboarding path. It stores/uses powerful administration credentials and increases lateral-movement value. Keep it only as an explicitly enabled connector if pilot customers prove a need.

## Security/release groundwork required before pilot

Before feature expansion:

- remove tracked virtual environments, runtime databases, caches and local state;
- use deterministic dependency resolution for production builds;
- run containers as non-root where possible;
- isolate network scanner privileges from the main web API;
- add auth/tenant/integration regression coverage;
- produce signed/versioned endpoint artifacts;
- add SBOM and build provenance;
- scan release images/packages for vulnerabilities;
- maintain one compatibility manifest for Wazuh versions across all platforms;
- protect security-sensitive paths with review ownership;
- maintain an immutable administrative audit trail.

## 90-day validation gate

Do not commit to a large product program before these conditions are tested.

Minimum continuation signals:

| Gate | Target |
|---|---:|
| Serious design partners | ≥3 organizations, preferably ≥2 MSPs |
| Real endpoint pilot | ≥200 total endpoints, or ≥3 real organizations for smaller fleets |
| Independent deployment | ≥2 deployments without developer intervention |
| Appliance setup | p50 <30 min; p95 <60 min to first useful security view |
| Endpoint enrolment | ≥95% unattended first-attempt success on supported OS matrix |
| Commercial signal | ≥2 pilots willing to pay, sign an LOI, or show a procurement path |
| Tenant isolation | 100% automated negative/cross-tenant tests pass |
| Release security | signed artifacts + SBOM/provenance; no unwaived exploitable Critical/High release vulnerability |

If the commercial/user-value gates fail, the decision is **archive as a portfolio/reference project** — not “replace Wazuh and try again.”

## Kill criteria

Stop product development and preserve the project as a portfolio artifact if, after the validation period:

- fewer than three serious design partners engage;
- pilots require persistent developer intervention to deploy or operate;
- MSPs prefer operating Wazuh/native tools directly and do not value the Cloud-X abstraction;
- no credible willingness-to-pay/procurement path emerges;
- support burden remains too high for the endpoint count;
- tenant isolation or release security cannot be made reliable at reasonable cost;
- the product's only remaining differentiator is “a nicer Wazuh dashboard.”

## Competitive reality

The target market is validated but crowded. Managed security vendors already sell low-operations security and MSP workflows. Cloud-X therefore cannot claim uniqueness based only on “security made easy for SMBs.”

Cloud-X must prove that **self-hosted/private security + low-touch orchestration + MSP evidence/reporting** is meaningfully better for a specific customer segment.

## Recommended decision sequence

1. Consolidate the repositories and clean release/security debt.
2. Implement the engine adapter and appliance bootstrap.
3. Turn installer work into versioned trusted endpoint enrolment.
4. Build only four routine operator surfaces: customers/sites, endpoint health, actionable findings and reports.
5. Pilot with real design partners.
6. Measure deployment effort, support interventions, finding usefulness, reporting value and commercial intent.
7. Continue only if the gate is met.

## Selected primary sources

- Wazuh API: https://documentation.wazuh.com/current/user-manual/api/index.html
- Wazuh centralized configuration: https://documentation.wazuh.com/current/user-manual/reference/centralized-configuration.html
- Wazuh groups: https://documentation.wazuh.com/current/user-manual/agent/agent-management/grouping-agents.html
- Wazuh dashboard: https://documentation.wazuh.com/current/getting-started/components/wazuh-dashboard.html
- Wazuh quickstart/sizing: https://documentation.wazuh.com/current/quickstart.html
- osquery: https://github.com/osquery/osquery
- OpenSearch: https://opensearch.org/
- Suricata EVE JSON: https://docs.suricata.io/en/latest/output/eve/eve-json-output.html
- Zeek: https://docs.zeek.org/en/current/about/what.html
- Velociraptor: https://docs.velociraptor.app/
- Greenbone Community Edition: https://greenbone.github.io/docs/latest/
- Microsoft code signing: https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options
- Apple Developer ID / notarization: https://developer.apple.com/support/developer-id/
- Debian APT key guidance: https://manpages.debian.org/testing/apt/apt-key.8.en.html
- GitHub Actions secure use: https://docs.github.com/en/actions/reference/security/secure-use
- Sigstore Cosign: https://docs.sigstore.dev/cosign/signing/signing_with_containers/

## Bottom line

The strategically sound bet is narrow and falsifiable:

> **Use Wazuh to avoid rebuilding commodity security plumbing. Spend the validation budget proving that Cloud-X can make that plumbing dramatically easier for SMBs/MSPs to deploy, operate and report on. If that value cannot be demonstrated quickly, archive the project proudly as a substantial security-engineering portfolio project.**
