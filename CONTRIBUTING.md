# Contributing to Cloud-X

Cloud-X uses a fixed branch topology.

## Maintainer and coding-agent flow

Coding agents work only on the permanent `feature/backend` or `feature/frontend` lanes and open pull requests to `dev`. They do not self-merge.

## External contributors

For now, external contributors should use a branch in their own fork and open a pull request to `dev`. Same-repository contributor topic branches are not part of the active policy.

## Promotion

- `feature/backend -> dev`: squash merge
- `feature/frontend -> dev`: squash merge
- `dev -> staging`: merge commit
- `staging -> main`: merge commit
- `main -> dev`: controlled reconciliation

`main` is production/default and is not a general work queue.
