#!/usr/bin/env python3
"""Cloud-X branch-policy validator and report-only classifier."""
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
    required = {"version", "mode", "permanent_branches", "agent_lanes", "edges", "bounded_prefixes", "automation"}
    missing = required - set(policy)
    if missing:
        raise PolicyError(f"missing keys: {sorted(missing)}")
    if policy["mode"] not in {"report-only", "enforce"}:
        raise PolicyError("mode must be report-only or enforce")
    if policy["permanent_branches"] != EXPECTED_PERMANENT:
        raise PolicyError("permanent branches must be exactly: " + ", ".join(EXPECTED_PERMANENT))
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

def classify_branch(branch: str, policy: dict) -> tuple[str, str]:
    if branch in policy["permanent_branches"]:
        return "permanent", branch
    for prefix, config in policy["bounded_prefixes"].items():
        if not branch.startswith(prefix):
            continue
        suffix = branch[len(prefix):]
        if not suffix or suffix.startswith("/") or ".." in suffix or any(c.isspace() for c in suffix):
            return "violation", f"unsafe suffix for {prefix}"
        if config.get("enabled"):
            return "bounded", prefix
        return "future-disabled", prefix
    return "violation", "unknown branch type"

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "classify", "check"))
    parser.add_argument("branch", nargs="?")
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
    if not args.branch:
        parser.error("branch is required for classify/check")
    status, detail = classify_branch(args.branch, policy)
    print(f"{args.branch}: {status} ({detail})")
    if args.command == "check" and status in {"violation", "future-disabled"}:
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
