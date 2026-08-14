# Cloud-X Repository Map and Consolidation Plan

Cloud-X historically evolved across three repositories. This document establishes one source of truth before the next coding phase.

## Canonical repository

### `MAPLEIZER/Cloud-X-MVP`

**Role:** canonical Cloud-X product repository during the 90-day validation phase.

New product architecture, API contracts, UI flows, packaging specifications, tests and documentation belong here unless a component has a deliberate independent release lifecycle.

## Related repositories

### `MAPLEIZER/Cloud-X-security-agent`

Repository: https://github.com/MAPLEIZER/Cloud-X-security-agent

**Historical value:** Windows/Linux installer work, Wazuh configuration/policy work and endpoint setup experiments.

**Plan:**

1. inventory unique installer/policy logic;
2. compare it with the hardened installer copies already present in the canonical repo;
3. migrate only the best/current implementation;
4. preserve attribution/provenance;
5. replace raw mutable-branch administrator installation instructions with a legacy warning;
6. archive the repository after migration is complete.

This repository must not become a second persistent Cloud-X endpoint agent product. The intended endpoint is the supported upstream Wazuh agent plus Cloud-X bootstrap/enrolment packaging.

### `MAPLEIZER/Cloud-X-Dashboard`

Repository: https://github.com/MAPLEIZER/Cloud-X-Dashboard

**Historical value:** earlier UI/dashboard exploration and possible reusable frontend components.

**Plan:**

1. identify genuinely unique Cloud-X UI work;
2. preserve upstream shadcn-admin/shadcn provenance for adapted work;
3. remove runtime/development artifacts from the current tree;
4. migrate useful UI pieces into the canonical frontend only when they fit the new product workflow;
5. archive the repository after migration/provenance cleanup.

The Dashboard repository is not a second frontend to keep feature-compatible.

## Migration rule

Do not copy a file simply because it exists in a legacy repo. A migrated component must have:

- a clear owner and purpose in the new architecture;
- no newer equivalent already in the canonical repo;
- security review where it performs privileged behavior;
- test coverage appropriate to its role;
- retained third-party provenance/license information.

## Target canonical layout

The existing repository will be migrated incrementally toward:

```text
Cloud-X-MVP/
├── apps/
│   ├── web/                    # Cloud-X product UI
│   └── api/                    # control-plane API
├── services/
│   ├── scanner-worker/
│   └── notification-worker/
├── integrations/
│   └── wazuh/                  # initial SecurityEngine provider
├── policy-packs/
├── packaging/
│   ├── windows/
│   ├── linux/
│   └── macos/
├── deploy/
│   └── compose/
├── tests/
├── docs/
├── LICENSE
└── THIRD_PARTY_NOTICES.md
```

Do not perform a large folder-only rewrite before tests/adapter boundaries exist. Move code as its responsibility becomes clear.

## Archive gate for legacy repositories

A legacy repository can be archived once:

- unique useful source has been migrated or intentionally rejected;
- provenance is documented;
- current-tree secrets/runtime data have been removed;
- README clearly points to the canonical repository;
- no active deployment process depends on it.
