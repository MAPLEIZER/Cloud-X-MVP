# Cloud-X Branch Strategy

Cloud-X adopts the permanent-lane model from the supplied MissionKit Branch Governance Blueprint with staged enforcement.

## Permanent branches

| Branch | Purpose | Normal outbound edge | Merge method |
|---|---|---|---|
| `feature/backend` | Backend, security, infrastructure, CI, governance, tests and mixed changes | `dev` | squash |
| `feature/frontend` | Frontend-only work | `dev` | squash |
| `dev` | Integration | `staging` | merge commit |
| `staging` | Release candidate / pre-production | `main` | merge commit |
| `main` | Production/default | controlled reconciliation to `dev` | reconcile |

Exactly these five branches are permanent.

## Current rollout state

**Mode: report-only.**

Implemented now:
- permanent branch topology;
- machine-readable branch policy and schema;
- owner-gated merge model;
- policy validation and unit tests;
- CI coverage of all permanent branches;
- CODEOWNERS coverage for governance paths;
- backend image publication removed from automatic CI;
- inventory of existing nonconforming branches without deletion.

Deliberately not enabled yet:
- branch-manager writers;
- automatic promotion branches;
- lane force-sync;
- automatic recovery tagging/deletion;
- security-autofix writers;
- autonomous bot merging;
- global auto-delete;
- auto-merge.

Existing legacy and bot branches are inventory, not proof that those branch types are approved writer lanes.

## Delivery truth

Keep these states separate: work produced, committed, pushed, PR open, merged. An agent may report handoff when its lane commit is pushed and the correct PR is open, but it must not claim merge or promotion.

## Bootstrap rule

No existing nonconforming branch is deleted or reset during Phase 0/1. Destructive cleanup waits for an inventory of unique commits and explicit recovery handling.
