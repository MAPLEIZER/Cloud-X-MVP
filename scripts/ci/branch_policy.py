#!/usr/bin/env python3
"""Cloud-X branch-policy validator, classifier, and PR-route enforcement."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / ".missionkit" / "branch-policy.json"
EXPECTED_PERMANENT = ["main", "staging", "dev", "feature/backend", "feature/frontend"]
EXPECTED_EDGES = {
    "feature/backend->dev": "squash",
    "feature/frontend->dev": "squash",
    "dev->staging": "merge_commit",
    "staging->main": "merge_commit",
    "main->dev": "reconcile",
}
VALID_MERGE_STRATEGIES = {"squash", "merge_commit", "reconcile"}


class PolicyError(ValueError):
    pass


def load_policy(path: Path = POLICY_PATH) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validate_policy(policy: dict) -> None:
    required = {
        "version",
        "mode",
        "permanent_branches",
        "agent_lanes",
        "edges",
        "bounded_prefixes",
        "automation",
    }
    missing = required - set(policy)
    if missing:
        raise PolicyError(f"missing keys: {sorted(missing)}")
    if policy["mode"] not in {"report-only", "enforce"}:
        raise PolicyError("mode must be report-only or enforce")
    if policy["permanent_branches"] != EXPECTED_PERMANENT:
        raise PolicyError(
            "permanent branches must be exactly: " + ", ".join(EXPECTED_PERMANENT)
        )
    lanes = policy["agent_lanes"]
    if lanes != {"backend": "feature/backend", "frontend": "feature/frontend"}:
        raise PolicyError("agent lane mapping is invalid")
    if any(branch not in policy["permanent_branches"] for branch in lanes.values()):
        raise PolicyError("every agent lane must be permanent")
    edges = policy["edges"]
    if set(edges) != set(EXPECTED_EDGES):
        raise PolicyError("edge set does not match Cloud-X governance graph")
    for edge, expected_strategy in EXPECTED_EDGES.items():
        config = edges[edge]
        if config.get("merge_strategy") not in VALID_MERGE_STRATEGIES:
            raise PolicyError(f"{edge}: unsupported merge strategy")
        if config.get("merge_strategy") != expected_strategy:
            raise PolicyError(f"{edge}: wrong merge strategy")
        if config.get("owner_gated") is not True:
            raise PolicyError(f"{edge}: merge must be owner-gated")

    automation = policy["automation"]
    if automation.get("owner_gated_merges") is not True:
        raise PolicyError("owner-gated merges must remain enabled")
    if automation.get("auto_merge") is not False:
        raise PolicyError("auto-merge must remain disabled")
    if automation.get("delete_branch_on_merge") is not False:
        raise PolicyError("global delete-on-merge must remain disabled")

    if policy["mode"] == "report-only":
        for key in ("branch_manager_enabled", "lane_sync_enabled", "audit_apply_enabled"):
            if automation.get(key) is not False:
                raise PolicyError(f"{key} must be false in report-only mode")

    if policy["mode"] == "enforce":
        enforcement = policy.get("enforcement", {})
        for key in ("pr_routing", "push_classification", "scheduled_audit"):
            if enforcement.get(key) is not True:
                raise PolicyError(f"{key} must be true in enforce mode")
        if enforcement.get("destructive_recovery") is not False:
            raise PolicyError(
                "destructive recovery remains disabled until recovery is proven"
            )
        for key in ("branch_manager_enabled", "audit_apply_enabled"):
            if automation.get(key) is not True:
                raise PolicyError(f"{key} must be true in enforce mode")
        if automation.get("lane_sync_enabled") is not False:
            raise PolicyError("lane sync must remain owner-controlled")
        dep = policy["bounded_prefixes"].get("dependabot/", {})
        if dep.get("mode") != "enforce" or dep.get("pr_base") != "dev":
            raise PolicyError("Dependabot must be enforced through dev")
        if dep.get("requires_open_pr") is not True:
            raise PolicyError("Dependabot branches must require an open PR")


def classify_branch(branch: str, policy: dict) -> tuple[str, str]:
    if branch in policy["permanent_branches"]:
        return "permanent", branch
    for prefix, config in policy["bounded_prefixes"].items():
        if not branch.startswith(prefix):
            continue
        suffix = branch[len(prefix) :]
        if (
            not suffix
            or suffix.startswith("/")
            or ".." in suffix
            or any(c.isspace() for c in suffix)
        ):
            return "violation", f"unsafe suffix for {prefix}"
        if config.get("enabled"):
            return "bounded", prefix
        return "future-disabled", prefix
    return "violation", "unknown branch type"


def validate_pr_route(
    head: str,
    base: str,
    actor: str,
    head_repo: str,
    repository: str,
    policy: dict,
) -> None:
    """Raise PolicyError when a PR violates the authorized graph."""
    if head_repo and head_repo != repository:
        if base != "dev":
            raise PolicyError("external contributor PRs must target dev")
        if actor.endswith("[bot]"):
            raise PolicyError("bot PRs may not use the fork-contributor exception")
        return
    if head in {"feature/backend", "feature/frontend"}:
        if base != "dev":
            raise PolicyError(f"{head} must target dev")
        return
    if head == "dev":
        if base != "staging":
            raise PolicyError("dev may only promote to staging")
        return
    if head == "staging":
        if base != "main":
            raise PolicyError("staging may only promote to main")
        return
    if head == "main":
        if base != "dev":
            raise PolicyError("main may only reconcile to dev")
        return
    if head.startswith("dependabot/"):
        dep = policy["bounded_prefixes"]["dependabot/"]
        if actor != dep.get("required_actor", "dependabot[bot]"):
            raise PolicyError("Dependabot namespace requires the verified Dependabot actor")
        if base != dep["pr_base"]:
            raise PolicyError("Dependabot PRs must target dev")
        return
    status, detail = classify_branch(head, policy)
    raise PolicyError(f"PR head is not authorized: {status} ({detail})")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "classify", "check", "check-pr"))
    parser.add_argument("branch", nargs="?")
    parser.add_argument("--head")
    parser.add_argument("--base")
    parser.add_argument("--actor", default="")
    parser.add_argument("--head-repo", default="")
    parser.add_argument("--repository", default="")
    args = parser.parse_args()
    try:
        policy = load_policy()
        validate_policy(policy)
    except (OSError, json.JSONDecodeError, PolicyError) as exc:
        print(f"branch-policy: invalid policy: {exc}", file=sys.stderr)
        return 2
    if args.command == "validate":
        print("branch-policy: valid")
        return 0
    if args.command == "check-pr":
        if not args.head or not args.base or not args.repository:
            parser.error("--head, --base and --repository are required for check-pr")
        try:
            validate_pr_route(
                args.head,
                args.base,
                args.actor,
                args.head_repo,
                args.repository,
                policy,
            )
        except PolicyError as exc:
            print(f"branch-policy: PR route denied: {exc}", file=sys.stderr)
            return 2
        print(f"branch-policy: PR route allowed: {args.head} -> {args.base}")
        return 0
    if not args.branch:
        parser.error("branch is required for classify/check")
    status, detail = classify_branch(args.branch, policy)
    print(f"{args.branch}: {status} ({detail})")
    if args.command == "check" and status in {"violation", "future-disabled"}:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
