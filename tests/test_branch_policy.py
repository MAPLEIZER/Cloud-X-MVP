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

    def test_agent_lane_mapping_is_permanent(self):
        self.assertEqual(self.policy["agent_lanes"], {"backend": "feature/backend", "frontend": "feature/frontend"})
        self.assertTrue(set(self.policy["agent_lanes"].values()) <= set(self.policy["permanent_branches"]))

    def test_merge_strategy_is_correct_for_every_edge(self):
        expected = {"feature/backend->dev": "squash", "feature/frontend->dev": "squash", "dev->staging": "merge_commit", "staging->main": "merge_commit", "main->dev": "reconcile"}
        self.assertEqual({edge: cfg["merge_strategy"] for edge, cfg in self.policy["edges"].items()}, expected)

    def test_unknown_topic_branch_is_denied(self):
        self.assertEqual(branch_policy.classify_branch("agent/random-task", self.policy)[0], "violation")

    def test_future_manager_namespaces_are_not_writer_lanes_yet(self):
        for branch in ("promote/dev-to-staging-x", "salvage/old-work"):
            self.assertEqual(branch_policy.classify_branch(branch, self.policy)[0], "future-disabled")

    def test_dependabot_is_report_only_and_never_auto_merge(self):
        dep = self.policy["bounded_prefixes"]["dependabot/"]
        self.assertTrue(dep["enabled"])
        self.assertEqual(dep["mode"], "report-only")
        self.assertTrue(dep["never_auto_merge"])
        self.assertEqual(dep["pr_base"], "dev")

    def test_automation_is_report_only(self):
        automation = self.policy["automation"]
        self.assertFalse(automation["branch_manager_enabled"])
        self.assertFalse(automation["lane_sync_enabled"])
        self.assertFalse(automation["audit_apply_enabled"])
        self.assertFalse(automation["auto_merge"])
        self.assertFalse(automation["delete_branch_on_merge"])
        self.assertTrue(automation["owner_gated_merges"])

    def test_ci_declares_every_permanent_branch(self):
        workflow = (ROOT / ".github" / "workflows" / "branch-policy.yml").read_text(encoding="utf-8")
        for branch in self.policy["permanent_branches"]:
            self.assertIn(branch, workflow)

    def test_backend_image_publish_is_manual_only(self):
        workflow = (ROOT / ".github" / "workflows" / "backend-image.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", workflow)
        self.assertNotIn("\n  push:", workflow)

    def test_codeql_language_policy_excludes_cpp(self):
        guidance = (ROOT / "docs" / "operations" / "CODEQL.md").read_text(encoding="utf-8")
        self.assertIn("javascript-typescript", guidance)
        self.assertIn("python", guidance)
        self.assertIn("C/C++ must not be selected", guidance)

if __name__ == "__main__":
    unittest.main()
