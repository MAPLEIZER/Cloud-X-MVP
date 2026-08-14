# Cloud-X Agent Branch Rules

Cloud-X uses two permanent coding lanes.

- Backend, infrastructure, CI, governance, security, tests, documentation that changes behavior, and mixed changes: `feature/backend`
- Frontend-only changes: `feature/frontend`

Agents MUST NOT create task, issue, `agent/*`, `fix/*`, or ad-hoc feature branches.

Normal delivery:

1. work and push on the assigned permanent lane;
2. open or update the lane PR to `dev`;
3. stop at handoff unless the repository owner explicitly performs the merge;
4. lane PRs use squash merge;
5. `dev -> staging` and `staging -> main` promotions use merge commits;
6. `main -> dev` is controlled reconciliation only.

During the current bootstrap, branch-manager, lane-sync, cleanup and security-autofix automation are intentionally disabled. The policy is report-only.

See `docs/operations/BRANCH_STRATEGY.md` and `.missionkit/branch-policy.json`.
