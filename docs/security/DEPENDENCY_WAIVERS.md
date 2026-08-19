# Dependency security waivers

Cloud-X dependency-security CI is intended to fail on known vulnerabilities. A waiver is permitted only when a stable upstream remediation is not available and the exception is explicit, narrow, time-bounded and tracked by an open security issue.

A waiver is **not** evidence that a vulnerability is fixed or irrelevant.

## Active waivers

None.

## Resolved waiver history

### PYSEC-2026-3552 — `cryptography`

| Field | Value |
|---|---|
| Status | Removed |
| Opened | 2026-08-18 |
| Removal initiated | 2026-08-19 |
| Tracking issue | #99 |
| Previously affected package found by audit | `cryptography 48.0.1` |
| Interim Cloud-X range | `cryptography>=49.0.0,<50` |
| Upstream fixed release | `50.0.0` |
| Upstream stable release date | 2026-07-31 |
| Cloud-X fixed range | `cryptography>=50.0.0,<51` |
| CI exception | Removed from ordinary dependency CI and release-time audit |

The original 2026-08-18 audit also reported `PYSEC-2026-3553` and `PYSEC-2026-3554`, both fixed by 49.0.0. Cloud-X raised its floor to 49.0.0 immediately and temporarily waived only `PYSEC-2026-3552` because its feed-listed fix, 50.0.0, was not yet a stable published release at that review point.

pyca/cryptography subsequently published stable 50.0.0 on 2026-07-31. Cloud-X therefore removes the upper bound that prevented 50.x, sets a 50.x security floor, and removes the exact advisory suppression from both `.github/workflows/dependency-security.yml` and `.github/workflows/release.yml`.

The removal change may merge only when the normal Python dependency audit passes without `--ignore-vuln`, the backend regression suite passes on the resolved 50.x environment, and all permanent-branch governance/build gates are green. Issue #99 is closed only after that evidence exists.

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
