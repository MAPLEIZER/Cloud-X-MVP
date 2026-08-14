from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "ci"))
import branch_policy  # noqa: E402

class BranchPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = branch_policy.load_policy()
        branch_policy.validate_policy(cls.policy)

    def test_exactly_five_permanent_branches(self):
        self.assertEqual(self.policy["permanent_branches"], ["main", "staging", "dev", "feature/backend", "feature/frontend"])

    def test_enforcement_mode_is_active_without_destructive_recovery(self):
        self.assertEqual(self.policy["mode"], "enforce")
        enforcement = self.policy["enforcement"]
        self.assertTrue(enforcement["pr_routing"])
        self.assertTrue(enforcement["push_classification"])
        self.assertTrue(enforcement["scheduled_audit"])
        self.assertFalse(enforcement["destructive_recovery"])

    def test_agent_lane_mapping_is_permanent(self):
        self.assertEqual(self.policy["agent_lanes"], {"backend": "feature/backend", "frontend": "feature/frontend"})
        self.assertTrue(set(self.policy["agent_lanes"].values()) <= set(self.policy["permanent_branches"]))

    def test_merge_strategy_is_correct_for_every_edge(self):
        expected = {"feature/backend->dev": "squash", "feature/frontend->dev": "squash", "dev->staging": "merge_commit", "staging->main": "merge_commit", "main->dev": "reconcile"}
        self.assertEqual({edge: cfg["merge_strategy"] for edge, cfg in self.policy["edges"].items()}, expected)

    def test_unknown_topic_branch_is_denied(self):
        self.assertEqual(branch_policy.classify_branch("agent/random-task", self.policy)[0], "violation")

    def test_future_manager_namespaces_are_disabled(self):
        for branch in ("promote/dev-to-staging-x", "salvage/old-work"):
            self.assertEqual(branch_policy.classify_branch(branch, self.policy)[0], "future-disabled")

    def test_dependabot_is_enforced_through_dev(self):
        dep = self.policy["bounded_prefixes"]["dependabot/"]
        self.assertTrue(dep["enabled"])
        self.assertEqual(dep["mode"], "enforce")
        self.assertEqual(dep["pr_base"], "dev")
        self.assertEqual(dep["required_actor"], "dependabot[bot]")
        self.assertTrue(dep["never_auto_merge"])

    def test_valid_lane_routes(self):
        branch_policy.validate_pr_route("feature/backend", "dev", "MAPLEIZER", "MAPLEIZER/Cloud-X-MVP", "MAPLEIZER/Cloud-X-MVP", self.policy)
        branch_policy.validate_pr_route("feature/frontend", "dev", "MAPLEIZER", "MAPLEIZER/Cloud-X-MVP", "MAPLEIZER/Cloud-X-MVP", self.policy)

    def test_invalid_lane_route_is_rejected(self):
        with self.assertRaises(branch_policy.PolicyError):
            branch_policy.validate_pr_route("feature/backend", "main", "MAPLEIZER", "MAPLEIZER/Cloud-X-MVP", "MAPLEIZER/Cloud-X-MVP", self.policy)

    def test_dependabot_provenance_and_base_are_required(self):
        branch_policy.validate_pr_route("dependabot/pip/x", "dev", "dependabot[bot]", "MAPLEIZER/Cloud-X-MVP", "MAPLEIZER/Cloud-X-MVP", self.policy)
        with self.assertRaises(branch_policy.PolicyError):
            branch_policy.validate_pr_route("dependabot/pip/x", "main", "dependabot[bot]", "MAPLEIZER/Cloud-X-MVP", "MAPLEIZER/Cloud-X-MVP", self.policy)
        with self.assertRaises(branch_policy.PolicyError):
            branch_policy.validate_pr_route("dependabot/pip/x", "dev", "MAPLEIZER", "MAPLEIZER/Cloud-X-MVP", "MAPLEIZER/Cloud-X-MVP", self.policy)

    def test_fork_only_contributor_route(self):
        branch_policy.validate_pr_route("feature/my-fork", "dev", "alice", "alice/Cloud-X-MVP", "MAPLEIZER/Cloud-X-MVP", self.policy)
        with self.assertRaises(branch_policy.PolicyError):
            branch_policy.validate_pr_route("feature/my-fork", "main", "alice", "alice/Cloud-X-MVP", "MAPLEIZER/Cloud-X-MVP", self.policy)

    def test_automation_remains_owner_gated(self):
        automation = self.policy["automation"]
        self.assertFalse(automation["branch_manager_enabled"])
        self.assertFalse(automation["lane_sync_enabled"])
        self.assertFalse(automation["audit_apply_enabled"])
        self.assertFalse(automation["auto_merge"])
        self.assertFalse(automation["delete_branch_on_merge"])
        self.assertTrue(automation["owner_gated_merges"])

    def test_enforcement_workflow_is_non_destructive(self):
        workflow = (ROOT / ".github" / "workflows" / "branch-enforcement.yml").read_text(encoding="utf-8")
        self.assertIn("Branch Policy Enforcement", workflow)
        self.assertNotIn("contents: write", workflow)
        self.assertNotIn("DELETE", workflow)

    def test_dependabot_targets_dev(self):
        config = (ROOT / ".github" / "dependabot.yml").read_text(encoding="utf-8")
        self.assertEqual(config.count('target-branch: "dev"'), 5)

if __name__ == "__main__":
    unittest.main()
