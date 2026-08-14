# Cloud-X Product Roadmap

**Roadmap reset:** 14 August 2026  
**Strategy:** conditional 90-day product validation  
**Initial engine:** Wazuh behind a Cloud-X-owned adapter  
**Fallback:** archive as a portfolio/reference project if the validation gate fails

## North star

Cloud-X should not compete by recreating SIEM/EDR internals. It should reduce the operational burden of deploying and running an open security stack for SMBs and MSPs.

The north-star workflow is:

```text
Deploy Cloud-X
  → create customer/site
  → generate trusted endpoint enrolment package
  → deploy through existing RMM/MDM/GPO/config management
  → first healthy endpoints appear
  → Cloud-X groups raw events into a small actionable finding set
  → operator reviews or applies an approved remediation
  → customer/MSP receives evidence and monthly report
```

## Non-goals

Before the validation gate, do **not** build:

- a new SIEM/search engine;
- a proprietary persistent endpoint agent;
- a generic Wazuh dashboard clone;
- unrestricted script execution;
- full packet capture;
- Kubernetes deployment merely for architectural completeness;
- simultaneous Wazuh + Velociraptor + Suricata + Zeek + Greenbone integrations;
- billing before customers prove product value;
- “AI SOC” features that are not tied to an operator workflow and measurable outcome.

## Phase 0 — Repository and release foundation

**Objective:** one source of truth before new feature coding.

### Repository consolidation

- [ ] Keep `Cloud-X-MVP` as canonical repository during validation.
- [ ] Link `Cloud-X-security-agent` and `Cloud-X-Dashboard` explicitly to the canonical repo.
- [ ] Inventory unique installer/policy/UI work in the two legacy repos.
- [ ] Migrate useful code with provenance rather than maintaining duplicate implementations.
- [ ] Archive legacy repositories after migration and cleanup.
- [ ] Remove generated/runtime artifacts from current trees.
- [ ] Perform a full Git-history secret/data scan before deciding whether history rewrite is required.

### Legal/provenance

- [x] Add MIT license for Cloud-X-authored code.
- [x] Add third-party notices/provenance baseline.
- [ ] Generate dependency/license inventory from exact lockfiles.
- [ ] Review copied/adapted legacy dashboard source and preserve upstream notices.

### Engineering baseline

- [ ] Define and test the `SecurityEngine` adapter contract.
- [ ] Create a single Wazuh compatibility manifest consumed by API and endpoint packaging.
- [ ] Move production Python dependencies to deterministic locked resolution with hashes.
- [ ] Run ordinary backend containers as non-root.
- [ ] Separate privileged scanner execution into a constrained worker/service.
- [ ] Establish protected release workflow, artifact signing, SBOM and provenance.
- [ ] Add auth, tenant-isolation and Wazuh contract tests.
- [ ] Add frontend unit tests and critical Playwright flows.

**Exit gate:** repository is clean enough that a tagged build can be reproduced and its dependencies/provenance explained.

---

## Phase 1 — SecurityEngine adapter and appliance bootstrap

**Objective:** Cloud-X can deploy and operate without exposing Wazuh internals to ordinary users.

### Adapter

Implement:

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

Initial provider: `WazuhSecurityEngine`.

Rules:

- no UI component calls Wazuh directly;
- Wazuh-specific identifiers are normalized before entering product workflows where practical;
- adapter calls are tenant-scoped and audited;
- compatibility tests run against every declared Wazuh version.

### Appliance bootstrap

Create a simple self-hosted/private-cloud deployment path, initially Docker Compose rather than Kubernetes.

Target bootstrap flow:

1. validate host resources and prerequisites;
2. create secrets;
3. initialize Cloud-X control plane;
4. provision/connect the Wazuh data plane;
5. configure TLS and application identity;
6. create first administrator/customer/site;
7. run health checks;
8. generate first endpoint enrolment profile.

**Target:** p50 <30 minutes and p95 <60 minutes to first useful security view during pilots.

---

## Phase 2 — Make installation a first-class product feature

**Objective:** reliable endpoint onboarding without Cloud-X becoming an RMM.

### Shared requirements

- one compatibility manifest across Windows/Linux/macOS;
- immutable versioned releases;
- one-time/short-lived enrolment token;
- structured install result and health verification;
- no installer fetched from mutable `main` as the supported path;
- no default SSH/WinRM administrator credential storage;
- support existing deployment tools through unattended options.

### Windows

- preserve upstream Wazuh Authenticode verification;
- produce a Cloud-X-signed bootstrap artifact;
- support Intune/RMM/GPO-friendly silent properties;
- verify installed version and service health;
- remove enrolment material after success.

### Linux

- produce controlled DEB/RPM/bootstrap release;
- use repository-scoped signing keyrings/fingerprint checks;
- pin supported Wazuh versions;
- avoid deprecated `apt-key` flow;
- avoid fragile XML manipulation when supported upstream configuration exists.

### macOS

- create signed Developer ID Installer package;
- notarize/staple release;
- verify upstream Wazuh package/signature/manifest;
- support Intel/Apple Silicon according to compatibility matrix;
- clearly document privacy/Full Disk Access requirements.

**Pilot target:** ≥95% unattended first-attempt enrolment success on supported OS matrix.

---

## Phase 3 — Opinionated operator workflow

**Objective:** prove that Cloud-X reduces operational complexity rather than simply reskinning Wazuh.

### Primary navigation

Keep the routine product surface intentionally small:

1. **Customers / Sites** — MSP/customer hierarchy, health and service state.
2. **Endpoints** — coverage, health, policy and stale/offline devices.
3. **Findings** — normalized actionable security problems.
4. **Reports / Evidence** — customer-facing posture and changes.

Native Wazuh administration remains an advanced escape hatch, not the default workflow.

### Initial finding classes

Start with a small set rather than every upstream rule:

- endpoint unhealthy/stale;
- critical software vulnerability;
- high-confidence suspicious execution/malware;
- security baseline drift;
- high-confidence authentication/identity anomaly where data supports it.

Every finding should answer:

- what happened?
- why does it matter?
- what assets/users are affected?
- what evidence supports it?
- what should the operator do next?
- is there a safe approved remediation?
- who acknowledged/resolved it and when?

### Safe response model

Build typed actions such as:

```text
isolate-approved-endpoint
restart-security-agent
apply-approved-policy
quarantine-validated-file
collect-approved-diagnostic
```

Do not expose a generic shell/script textbox as a normal product capability.

---

## Phase 4 — Reporting, evidence and integrations

**Objective:** turn technical security data into something MSPs can operate and sell.

### Monthly report MVP

- endpoint coverage and health;
- unresolved critical/high findings;
- vulnerability trend;
- policy/baseline conformance;
- significant events and resolutions;
- stale/unmanaged assets;
- changes since previous period;
- explicit limitations/coverage statement.

### Integrations

Prioritize operational systems already used by target customers:

- email;
- Microsoft Teams / Slack;
- generic webhooks;
- ticketing/RMM connectors based on pilot demand.

### Compliance/evidence packs

Treat Kenya/East Africa or industry-specific evidence packs as **content validated with auditors/MSPs**, not as assumed legal compliance automation. The product can map collected evidence to controls, but should not claim that using Cloud-X makes an organization compliant.

---

## Phase 5 — 90-day pilot and kill gate

**Objective:** decide whether this is a product or a portfolio project.

### Minimum continuation gates

| Metric | Minimum target |
|---|---:|
| Serious design partners | ≥3 organizations; preferably ≥2 MSPs |
| Real endpoint coverage | ≥200 endpoints, or ≥3 real organizations for smaller fleets |
| Independent deployment | ≥2 deployments without developer intervention |
| Setup time | p50 <30 min; p95 <60 min |
| Endpoint enrolment | ≥95% unattended first-attempt success |
| Commercial signal | ≥2 pilots willing to pay, sign LOI, or show procurement path |
| Cross-tenant negative tests | 100% pass |
| Production artifacts | 100% signed with SBOM/provenance |
| Known unwaived exploitable Critical/High release vulns | 0 |

### Operational measurements

Record:

- number of manual interventions per deployment;
- install failures by OS/cause;
- false/unactionable findings;
- time from finding to operator decision;
- report usefulness to MSP/customer;
- routine support touches per 50 endpoints/month;
- requests that require dropping into native Wazuh UI;
- customer willingness to pay and why.

### Kill criteria

Archive product development if the validation period shows that:

- the abstraction does not materially reduce Wazuh operating effort;
- design-partner engagement is weak;
- customers will not pay for the orchestration/evidence layer;
- deployments remain developer-dependent;
- tenant security or release engineering costs are disproportionate;
- the roadmap drifts back toward rebuilding SIEM internals.

Failure of this gate means **portfolio/archive**, not “build our own SIEM.”

---

## After validation — only if GO

### 6-month product target

- MSP control plane over isolated customer data planes;
- repeatable customer provisioning/deprovisioning;
- backup/restore/upgrade orchestration;
- policy/evidence packs validated by real operators;
- immutable admin audit log;
- stronger SSO/RBAC;
- independent penetration test;
- optional passive Suricata sensor if pilots demand network visibility.

Commercial gate: approximately ≥5 paying organizations or ≥2 paying MSPs and evidence that recurring support burden is manageable.

### 12-month target

Only where demand exists:

- scale/HA;
- mature MSP lifecycle/API integrations;
- offline/restricted-network release bundles;
- optional Velociraptor DFIR;
- optional Greenbone vulnerability scanning;
- optional Zeek network metadata;
- repeated external security assessment.

Do not add these merely to make the architecture look comprehensive.

## Work ordering for the next coding phase

1. Repository cleanup and source-of-truth consolidation.
2. `SecurityEngine` interface and Wazuh contract tests.
3. Compatibility manifest.
4. Appliance bootstrap.
5. Endpoint bootstrap release pipeline.
6. Endpoint health view.
7. Actionable finding normalization.
8. Reporting/evidence MVP.
9. Pilot instrumentation.
10. Pilot deployments and go/archive decision.

## Definition of success

Cloud-X succeeds if an MSP can operate a useful security service without becoming a Wazuh expert and without Cloud-X becoming a new high-risk remote administration platform.
