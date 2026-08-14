from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BranchPurgePolicyTests(unittest.TestCase):
    def test_policy_requires_archive_before_delete(self):
        policy = json.loads((ROOT / ".missionkit" / "branch-policy.json").read_text(encoding="utf-8"))
        enforcement = policy["enforcement"]
        self.assertEqual(enforcement["legacy_branch_cleanup"], "archive-tag-then-delete")
        self.assertEqual(enforcement["branch_purge_marker"], "[branch-purge]")
        self.assertFalse(enforcement["destructive_recovery"])

    def test_purge_workflow_is_marker_gated(self):
        workflow = (ROOT / ".github" / "workflows" / "branch-purge.yml").read_text(encoding="utf-8")
        self.assertIn("contains(github.event.head_commit.message, '[branch-purge]')", workflow)
        self.assertIn("contents: write", workflow)
        self.assertIn("archive_non_permanent_branches.sh", workflow)

    def test_purge_script_preserves_permanent_branches_and_open_pr_heads(self):
        script = (ROOT / "scripts" / "ci" / "archive_non_permanent_branches.sh").read_text(encoding="utf-8")
        for branch in ("main", "staging", "dev", "feature/backend", "feature/frontend"):
            self.assertIn(f'"{branch}"', script)
        self.assertIn("archive/branches/", script)
        self.assertIn("is_open_pr_head", script)
        self.assertIn('git push origin --delete "$branch"', script)


if __name__ == "__main__":
    unittest.main()
