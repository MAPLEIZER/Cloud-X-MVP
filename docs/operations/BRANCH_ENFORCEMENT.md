# Branch Enforcement Status

Cloud-X branch governance is now in **enforce** mode for routing and classification.

Active controls:
- PR routing is validated for `feature/backend -> dev`, `feature/frontend -> dev`, `dev -> staging`, `staging -> main`, and `main -> dev` reconciliation.
- Dependabot version-update PRs target `dev` and must be authored by `dependabot[bot]`.
- Pushes are classified against the allowed branch namespaces.
- An hourly audit verifies all five permanent branches still exist and reports legacy/nonconforming branches.
- A managed local pre-push hook blocks ordinary pushes from manager-owned branches when installed.

Not yet automatic:
- No branch is deleted automatically.
- No recovery tag is created automatically.
- No lane is reset by a bot.
- No promotion PR is created or merged by a bot.

Those destructive/manager capabilities remain disabled until recovery tagging, provenance checks, and rollback exercises are implemented and proven.

GitHub repository rulesets should require the stable `Branch Policy Enforcement` and normal CI checks on `dev`, `staging`, and `main`. The connected GitHub app can inspect the current ruleset but does not expose a ruleset mutation action, so repository-rule changes must be applied in GitHub Settings when not already present.
