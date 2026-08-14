#!/usr/bin/env bash
set -euo pipefail

: "${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
: "${GH_TOKEN:?GH_TOKEN is required}"

readonly -a PERMANENT_BRANCHES=(
  "main"
  "staging"
  "dev"
  "feature/backend"
  "feature/frontend"
)

is_permanent() {
  local candidate="$1"
  local branch
  for branch in "${PERMANENT_BRANCHES[@]}"; do
    [[ "$candidate" == "$branch" ]] && return 0
  done
  return 1
}

is_open_pr_head() {
  local candidate="$1"
  grep -Fxq -- "$candidate" "$OPEN_PR_HEADS_FILE"
}

api_get() {
  curl --fail --silent --show-error \
    -H "Accept: application/vnd.github+json" \
    -H "Authorization: Bearer ${GH_TOKEN}" \
    -H "X-GitHub-Api-Version: 2022-11-28" \
    "$1"
}

OPEN_PR_HEADS_FILE="$(mktemp)"
trap 'rm -f "$OPEN_PR_HEADS_FILE"' EXIT

# Keep the purge safe if an unexpected PR is still open. Pagination to 100 is
# sufficient for this repository's bounded branch model; if that ever changes,
# this script should be upgraded before use.
api_get "${GITHUB_API_URL}/repos/${GITHUB_REPOSITORY}/pulls?state=open&per_page=100" \
  | jq -r --arg repo "$GITHUB_REPOSITORY" '.[] | select(.head.repo.full_name == $repo) | .head.ref' \
  | sort -u > "$OPEN_PR_HEADS_FILE"

git config user.name "cloud-x-branch-archiver"
git config user.email "cloud-x-branch-archiver@users.noreply.github.com"
git fetch --prune --tags origin '+refs/heads/*:refs/remotes/origin/*'

mapfile -t branches < <(
  git for-each-ref refs/remotes/origin \
    --format='%(refname:strip=3)' \
    | grep -v '^HEAD$' \
    | sort -u
)

archived=0
deleted=0
skipped_open_pr=0

for branch in "${branches[@]}"; do
  [[ -n "$branch" ]] || continue

  if is_permanent "$branch"; then
    echo "KEEP permanent branch: $branch"
    continue
  fi

  if is_open_pr_head "$branch"; then
    echo "SKIP branch with open PR: $branch"
    ((skipped_open_pr += 1))
    continue
  fi

  tip="$(git rev-parse "refs/remotes/origin/${branch}")"
  archive_tag="archive/branches/${branch}"

  if git ls-remote --exit-code --tags origin "refs/tags/${archive_tag}" >/dev/null 2>&1; then
    existing="$(git ls-remote --tags origin "refs/tags/${archive_tag}" | awk '{print $1}' | head -n1)"
    if [[ "$existing" != "$tip" ]]; then
      echo "Archive tag already exists at a different commit: ${archive_tag}" >&2
      exit 1
    fi
    echo "KEEP existing archive tag: ${archive_tag} -> ${tip}"
  else
    git tag "$archive_tag" "$tip"
    git push origin "refs/tags/${archive_tag}:refs/tags/${archive_tag}"
    echo "ARCHIVE ${branch} -> ${archive_tag} @ ${tip}"
    ((archived += 1))
  fi

  # Delete only after the exact tip is recoverable through the archive tag.
  git push origin --delete "$branch"
  echo "DELETE branch: ${branch}"
  ((deleted += 1))
done

echo "Branch cleanup complete: archived=${archived} deleted=${deleted} skipped_open_pr=${skipped_open_pr}"
