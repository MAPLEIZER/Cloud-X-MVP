# Phase 0 Repository Inventory

**Inventory date:** 14 August 2026

This file records the consolidation decisions made before new Cloud-X product coding begins.

## Source of truth

`MAPLEIZER/Cloud-X-MVP` is the canonical repository during product validation.

## Canonical repository cleanup

Removed from the Phase 0 branch because they are generated/runtime state rather than source:

- tracked backend virtual environment (`cloudx-flask-backend/venv`);
- `.tanstack/` generated temporary files;
- Python scanner `__pycache__/` bytecode;
- `cloudx-flask-backend/sync_heartbeat.json`;
- `cloudx-flask-backend/test_sync.txt`.

The existing `.gitignore` already excludes these classes of files; Phase 0 removes the historical tracked copies.

The historical `scans.db` blob remains reachable in old Git history even though it is no longer in the canonical current tree. History rewriting is a separate destructive operation and is not performed as part of this Phase 0 branch.

## `Cloud-X-security-agent`

### Finding

The external repository is an August 2025 Windows-focused installer/configuration snapshot. Its executable PowerShell/active-response scripts are older than the hardened copies already present in the canonical repository.

Examples of historical differences include substantially larger legacy installer/uninstaller/post-install scripts and old mutable-`main` download instructions. The external README also contains stale hard-coded network assumptions and an old Wazuh package default.

### Decision

- Do **not** copy the old executable scripts back into the canonical tree.
- Preserve the repository as provenance for the installer/configuration work.
- Replace its README with a legacy-component notice and canonical-repository link.
- Add an explicit license/provenance baseline.
- Archive it only after no deployment process relies on the repository and all useful historical configuration has been accounted for.

The current hardened Windows installer/post-install/active-response implementation in `Cloud-X-MVP` is the forward baseline.

## `Cloud-X-Dashboard`

### Finding

The private repository is an August 2025 dashboard/backend snapshot. It includes generated TanStack state, Python bytecode and an old runtime `scans.db`. The canonical repository has since moved beyond this snapshot and includes the hardened backend/frontend work.

### Decision

- Treat the dashboard repository as a legacy UI/provenance snapshot, not an active application.
- Preserve upstream UI attribution where source was adapted from shadcn-admin/shadcn components.
- Remove current-tree generated/runtime artifacts before eventual archival.
- Migrate only genuinely unique UI work that supports the new Customers/Sites → Endpoints → Findings → Reports product workflow.
- Do not revive its duplicated Flask backend.

## Current installer baseline

Cloud-X already has source for Windows, Linux and macOS Wazuh installation in the canonical repository after the August 2026 security hardening. This is **not yet equivalent to a production packaging system**.

Phase 0/1 must turn those scripts into a controlled release path with:

- one compatibility manifest;
- immutable versions;
- signature/hash verification;
- short-lived enrolment material;
- structured health result;
- package signing/notarization appropriate to each OS;
- CI validation and SBOM/provenance.

## Deferred cleanup

The following are intentionally deferred until tests/ownership boundaries exist:

- large folder-only repository restructure;
- deletion of historical docs that may contain useful design provenance;
- removal of the embedded `cloudx-security-agent/` subtree;
- Git-history rewrite for old runtime database blobs;
- optional sensor integrations.

## Next engineering tasks

1. implement the `SecurityEngine` interface and `WazuhSecurityEngine` provider contract;
2. add Wazuh contract/integration tests against the compatibility manifest;
3. produce deterministic Python dependency resolution;
4. run ordinary backend containers non-root;
5. split privileged scanning from the main API process;
6. add auth/tenant negative tests;
7. add release signing, SBOM and provenance workflow;
8. complete legacy-repository migration notices and clean their current trees.
