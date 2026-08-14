# Cloud-X Branch Runbook

## Start backend or mixed work

1. Use `feature/backend`.
2. Confirm it is synchronized from `dev` before new work.
3. Make and test changes.
4. Push to the same permanent lane.
5. Open or update one PR: `feature/backend -> dev`.
6. Owner reviews and squash-merges.
7. Do not delete the permanent lane.

Frontend-only work follows the same process on `feature/frontend`.

## Promote an integrated release

1. Verify `dev` CI/security checks.
2. Open `dev -> staging`.
3. Owner merge-commits the promotion.
4. Validate staging.
5. Open `staging -> main`.
6. Re-run release gates.
7. Owner merge-commits.
8. Reconcile any owner hotfix on `main` back into `dev`.

## Existing unknown branches

During report-only rollout: classify and inventory; determine whether commits are unique; do not delete/reset; do not promote them directly to `main`.

Future cleanup must preserve unique work with recovery tags before branch deletion.

## Automation state

Manager, lane-sync and destructive audit automation remain disabled until their permissions and tests are ready.
