# Repository history hygiene record

Date: 2026-08-14

This record documents the artifact cleanup performed during Phase 0 without rewriting Git commit history.

## Current-tree status

The current tracked tree is expected to contain none of the following:

- SQLite/runtime database files (`*.db`, `*.sqlite`, `*.sqlite3`)
- committed Python virtual environments (`venv/`, `.venv/`)
- real `.env` files
- private-key-bearing files (`*.pfx`, `*.p12`, `*.key`, `*.pem`)
- the retired `cloudx-code-signing.cer` trust certificate

`tests/test_branch_repository_hygiene.py` enforces these rules in the Branch Policy gate and also verifies that the canonical `.env.example` documents frontend, Clerk, deployment-policy, PostgreSQL and Wazuh connector settings.

## Historical artifacts retained

### `cloudx-flask-backend/scans.db`

The SQLite runtime database was introduced with the earlier Flask scanning backend and was removed by commit `e7c1ef55593baab998263c4ee02d20c01198ddac` (`security: remove tracked runtime scan database`). The old blob remains reachable from historical commits.

The current application no longer uses SQLite; PostgreSQL plus Alembic is the supported datastore path.

### `cloudx-flask-backend/scripts/windows/cloudx-code-signing.cer`

The certificate was removed by commit `e530b180fe2dd7da46ee0140ed93a7c45c227d1d` (`security: remove obsolete project root-trust certificate`). It was a certificate/trust artifact, not a private signing key. The current Windows installer no longer installs this project certificate into the machine root store.

### Virtual environment

Historical development commits previously included virtual-environment content. The current tree contains no tracked `venv/`/`.venv/`, and the ignore/test policy prevents reintroduction.

## Why history was not rewritten

Removing these blobs from every historical commit would require a destructive repository rewrite (for example, `git filter-repo`) followed by force-updating branches/tags and coordinating every clone. Phase 0 deliberately preserved auditable commit and archive-tag history, so that rewrite is not performed as part of routine cleanup.

If a future data-classification review determines that historical scan telemetry itself must be cryptographically erased from the public Git history, treat that as a separate migration with an explicit backup, ref map, coordinated force-push, contributor notification, and post-rewrite verification.

## Credential rotation

The identified cleanup artifacts above do not provide a private signing key or a committed `.env` credential set to rotate. Runtime secrets are now represented only by placeholders in `.env.example` files and must be supplied out-of-band.

If any real Clerk, PostgreSQL, Wazuh, SSH, WinRM, registry or other credential is ever discovered in Git history, revoke/rotate it immediately; history rewriting alone is not a substitute for credential rotation.
