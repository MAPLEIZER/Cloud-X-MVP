# ADR 0001: Use Wazuh behind a Cloud-X SecurityEngine adapter

- **Status:** Accepted for validation
- **Date:** 2026-08-14

## Context

Cloud-X originally grew toward a broad security platform with its own dashboard, network scanning and endpoint-installation layer. Research found that rebuilding the endpoint, detection, inventory, vulnerability, FIM/SCA and response primitives already supplied by mature open-source platforms would consume the engineering budget without validating the customer problem.

The product hypothesis is instead that SMBs and MSPs may value a simpler self-hosted operating layer: reliable onboarding, tenant/customer workflows, actionable findings, safe remediation and evidence/reporting.

## Decision

Cloud-X will use Wazuh as the initial security engine behind a Cloud-X-owned `SecurityEngine` interface.

Customer-facing product code must not make Wazuh-specific API shapes the permanent Cloud-X domain model. The first provider is `WazuhSecurityEngine`; another provider may be introduced later only when a validated requirement justifies the cost.

Cloud-X owns:

- customer/site/endpoint lifecycle;
- deployment and enrolment workflows;
- policy abstractions;
- finding normalization;
- approved remediation catalog;
- reporting/evidence;
- product audit and health workflows.

Wazuh owns the initial implementation of endpoint telemetry, agent protocol, inventory, FIM/SCA, vulnerability data, low-level detection/rules and response primitives.

## Consequences

### Positive

- avoids rebuilding commodity security plumbing before product-market fit;
- preserves Wazuh as a replaceable implementation rather than the public product model;
- reduces the security surface Cloud-X must invent and maintain;
- allows pilot engineering to focus on operator value.

### Negative

- Cloud-X inherits upstream compatibility work and some operational complexity;
- adapter contract tests become mandatory;
- Wazuh licensing and distribution requirements must remain visible in release provenance;
- the native Wazuh UI remains necessary as an advanced troubleshooting escape hatch during validation.

## Revisit trigger

Revisit this decision only if real pilots demonstrate a hard product requirement Wazuh cannot satisfy reasonably, or if upstream licensing/architecture makes the validated Cloud-X delivery model impractical. Failure of the product validation gate is **not** by itself a reason to build a replacement SIEM.
