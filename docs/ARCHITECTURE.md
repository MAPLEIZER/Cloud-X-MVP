# Cloud-X Target Architecture

**Status:** architecture baseline for the post-research validation phase.

## Design principles

1. Cloud-X owns orchestration and product workflow, not commodity SIEM internals.
2. Wazuh is an implementation behind an adapter, not the public Cloud-X API model.
3. Customer isolation is a security boundary.
4. Endpoint deployment uses trusted packages and existing fleet-management channels by default.
5. Arbitrary remote execution is not a normal product primitive.
6. Privileged scanners/sensors are isolated from the ordinary web control plane.
7. Releases are immutable, attributable and verifiable.

## Logical architecture

```text
                         ┌───────────────────────┐
                         │ MSP / SMB Operator    │
                         └──────────┬────────────┘
                                    │
                         ┌──────────▼────────────┐
                         │ Cloud-X Web UI        │
                         │ React / TypeScript    │
                         └──────────┬────────────┘
                                    │
                         ┌──────────▼────────────┐
                         │ Cloud-X Control API   │
                         │ auth • tenants • RBAC │
                         └───┬──────┬──────┬────┘
                             │      │      │
                     ┌───────▼┐  ┌──▼───┐  └──────────────┐
                     │Product │  │Audit │                 │
                     │DB      │  │log   │                 │
                     └────────┘  └──────┘                 │
                                                         │
                                              ┌──────────▼─────────┐
                                              │ SecurityEngine     │
                                              │ adapter            │
                                              └──────────┬─────────┘
                                                         │
                       ┌─────────────────────────────────┼─────────────────────────────────┐
                       │                                 │                                 │
               ┌───────▼────────┐               ┌────────▼───────┐               ┌────────▼───────┐
               │ Customer A     │               │ Customer B     │               │ Customer C     │
               │ Wazuh plane    │               │ Wazuh plane    │               │ Wazuh plane    │
               └───────┬────────┘               └────────┬───────┘               └────────┬───────┘
                       │                                 │                                 │
                  endpoints                         endpoints                         endpoints
```

Early validation should favor isolated customer data planes over a globally shared security-data cluster. Shared infrastructure can be optimized later only after threat modeling and negative isolation testing.

## SecurityEngine interface

Cloud-X product code depends on a narrow provider interface rather than Wazuh-specific routes:

```python
class SecurityEngine:
    def list_endpoints(self, tenant): ...
    def enrolment_profile(self, tenant, site, policy): ...
    def apply_policy(self, tenant, target, policy): ...
    def list_findings(self, tenant, filters): ...
    def acknowledge_finding(self, tenant, finding_id, actor): ...
    def endpoint_inventory(self, tenant, endpoint_id): ...
    def endpoint_vulnerabilities(self, tenant, endpoint_id): ...
    def execute_approved_response(self, tenant, action, target): ...
    def health(self, tenant): ...
    def capabilities(self): ...
```

The exact Python signature can change during implementation; the architectural rule is the important part.

## Tenant model

Cloud-X should own a first-class hierarchy:

```text
MSP account
└── customer
    └── site
        └── endpoint
```

Every security-engine credential and API call is resolved in tenant context. Cross-tenant access should fail closed and be covered by negative tests.

## Endpoint enrolment

Normal path:

```text
Cloud-X
  → issue short-lived enrolment material
  → produce/reference signed versioned bootstrap
  → MSP deploys with RMM/MDM/GPO/config management
  → bootstrap verifies upstream package
  → installs supported Wazuh agent
  → enrols into correct tenant/site/policy group
  → reports structured success/health
  → deletes enrolment material
```

SSH/WinRM is not the default path. If retained at all, it is an optional connector with explicit permission boundaries and separate credential handling.

## Scanner architecture

Network scanners process operator-controlled targets but invoke privileged/high-impact tooling. Move scanning away from the main API process:

```text
Control API → validated scan job → constrained scanner worker → normalized result → product DB
```

The worker should have target/CIDR policy, quotas, timeout, immutable audit metadata and only the Linux capabilities needed by the selected scanner.

## Finding normalization

Wazuh may generate a large rule/event space. Cloud-X should map those inputs into a stable product taxonomy so the customer-facing UI does not depend on every upstream rule ID.

Example product finding:

```json
{
  "category": "critical_vulnerability",
  "severity": "critical",
  "tenant_id": "...",
  "endpoint_id": "...",
  "title": "Critical software vulnerability requires action",
  "evidence": [],
  "recommended_actions": [],
  "engine": "wazuh",
  "engine_refs": []
}
```

## Approved response model

Remote response is a high-risk capability. Use an allowlisted action catalog with typed parameters and audit records. The control plane should never turn user input into a general shell command.

## Release architecture

Every supported release should be traceable to:

- Cloud-X version/tag;
- Git commit;
- declared Wazuh compatibility;
- artifact hashes;
- signature/signing identity;
- SBOM digest;
- provenance/attestation;
- vulnerability scan result;
- license scan result.

## Future optional modules

Optional integrations must remain independently disableable:

- Suricata — passive NIDS/events;
- Zeek — network metadata;
- Velociraptor — DFIR/investigation;
- Greenbone — vulnerability scanning.

Their credentials and privileges should not share the Cloud-X signing trust domain or unrelated tenant secrets.
