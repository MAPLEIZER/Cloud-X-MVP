# Dependency security waivers

Cloud-X dependency-security CI is intended to fail on known vulnerabilities. A waiver is permitted only when a stable upstream remediation is not available and the exception is explicit, narrow, time-bounded and tracked by an open security issue.

A waiver is **not** evidence that a vulnerability is fixed or irrelevant.

## Active waivers

### PYSEC-2026-3552 — `cryptography`

| Field | Value |
|---|---|
| Status | Active — upstream blocked |
| Opened | 2026-08-18 |
| Review by | 2026-09-17 |
| Tracking issue | #99 |
| Affected package found by audit | `cryptography 48.0.1` |
| Cloud-X remediation already applied | floor raised to `cryptography>=49.0.0,<50` |
| Remaining feed-listed fix | `50.0.0` |
| Stable upstream availability at review | 50.0.0 is not released; upstream marks it as development |
| CI exception | exact ID `PYSEC-2026-3552` only |

The same 2026-08-18 audit also reported `PYSEC-2026-3553` and `PYSEC-2026-3554`, both of which list 49.0.0 as a fix. Those advisories are **not waived**; Cloud-X moved its stable cryptography floor to 49.0.0 so they must remain cleared by the ordinary audit.

Paramiko 5.0.0 declares `cryptography>=3.3` and therefore does not place an upper bound that prevents the stable 49.x remediation.

### Removal procedure

When a stable cryptography 50.x release becomes available:

1. review upstream security/release notes and platform changes;
2. update the Cloud-X cryptography range deliberately rather than consuming an unreleased build;
3. run backend regression, deployment and dependency-security CI;
4. remove `--ignore-vuln PYSEC-2026-3552` from `.github/workflows/dependency-security.yml`;
5. confirm the Python audit is green with no unwaived finding;
6. close #99 and remove this active waiver entry (or move it to a resolved-history section).

## Waiver rules

Any future dependency waiver must include:

- one exact advisory identifier, not a package-wide/severity-wide suppression;
- the affected and safe/fix versions reported by the audit feed;
- why a normal stable upgrade is not currently possible;
- a tracking issue with `type:security`, `status:blocked`, and an explicit priority;
- an expiry/review date no more than 30 days away during pre-production/pilot work;
- a defined removal test;
- owner approval before a release candidate is cut.

Critical or known-exploited vulnerabilities should not be waived for a supported release merely because remediation is inconvenient. If a safe dependency fix is unavailable, remove/disable the affected capability or block the release unless a documented risk decision explicitly says otherwise.
