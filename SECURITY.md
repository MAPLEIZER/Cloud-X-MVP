# Security Policy

## Project status

Cloud-X is currently **pre-production and under product validation**. No version is yet designated as a supported production security product.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting / security advisory workflow for this repository where available. Do **not** publish exploit details, credentials, customer data or sensitive reproduction material in a public issue.

Include, where possible:

- affected commit/tag;
- affected component and platform;
- impact and preconditions;
- minimal reproduction steps;
- suggested remediation if known.

## Security boundaries

The following areas are treated as security-sensitive and require focused review:

- authentication and tenant authorization;
- Wazuh/security-engine adapters and credentials;
- endpoint installers and enrolment material;
- active-response/remediation actions;
- SSH/WinRM or any remote-management connector;
- network scanners;
- release signing and CI/CD;
- secrets, backup and restore paths.

## Default product security rules

- Arbitrary remote shell is not a default Cloud-X product capability.
- Installer/bootstrap credentials should be one-time or short-lived.
- Production installer artifacts must be immutable, versioned and signed.
- Customer data planes and credentials must be isolated by tenant.
- Cross-tenant access is a release-blocking security defect.
- Build/signing systems must be isolated from customer-facing runtime services.
- No release may knowingly ship an unwaived exploitable Critical/High vulnerability.

## Supported versions

None yet. Supported-version and vulnerability-response commitments will be introduced when Cloud-X reaches a production release gate.
