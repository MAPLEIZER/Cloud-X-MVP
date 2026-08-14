#!/usr/bin/env bash
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
common_dir=$(git -C "$repo_root" rev-parse --git-common-dir)
if [[ "$common_dir" != /* ]]; then
  common_dir="$repo_root/$common_dir"
fi

hooks_dir="$common_dir/hooks"
mkdir -p "$hooks_dir"
install -m 0755 "$repo_root/.githooks/pre-push" "$hooks_dir/pre-push"
printf 'Installed Cloud-X managed pre-push hook at %s\n' "$hooks_dir/pre-push"
