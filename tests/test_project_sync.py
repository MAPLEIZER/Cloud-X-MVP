import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ci" / "sync_projects.py"
spec = importlib.util.spec_from_file_location("sync_projects", MODULE_PATH)
sync_projects = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = sync_projects
spec.loader.exec_module(sync_projects)


CONFIG = {
    "version": 1,
    "dimensions": {
        "status": {
            "label_prefix": "status:",
            "field_names": ["Status"],
            "cardinality": "one",
            "aliases": {
                "planned": ["Planned", "Todo"],
                "in-progress": ["In Progress"],
                "done": ["Done"],
            },
        },
        "phase": {
            "label_prefix": "phase:",
            "field_names": ["Phase"],
            "cardinality": "one",
            "aliases": {"2": ["Phase 2"]},
        },
        "area": {
            "label_prefix": "area:",
            "field_names": ["Areas", "Area"],
            "cardinality": "many",
            "aliases": {"security-engine": ["Security Engine"]},
        },
        "pipeline": {
            "label_prefix": "pipeline:",
            "field_names": ["Pipeline"],
            "cardinality": "one",
            "aliases": {"done": ["Done"], "next": ["Next"]},
        },
    },
    "state_overrides": {
        "closed": {"status": ["done"], "pipeline": ["done"]}
    },
}


class ProjectSyncPolicyTests(unittest.TestCase):
    def test_extracts_label_dimensions(self):
        result = sync_projects.extract_dimensions(
            ["status:planned", "phase:2", "area:backend", "area:security-engine"],
            "open",
            CONFIG,
        )
        self.assertEqual(result["status"], ["planned"])
        self.assertEqual(result["phase"], ["2"])
        self.assertEqual(result["area"], ["backend", "security-engine"])

    def test_closed_state_overrides_status_and_pipeline(self):
        result = sync_projects.extract_dimensions(
            ["status:in-progress", "pipeline:next"], "closed", CONFIG
        )
        self.assertEqual(result["status"], ["done"])
        self.assertEqual(result["pipeline"], ["done"])

    def test_conflicting_single_value_labels_fail(self):
        with self.assertRaises(sync_projects.ProjectSyncError):
            sync_projects.extract_dimensions(
                ["status:planned", "status:in-progress"], "open", CONFIG
            )

    def test_titleize_preserves_operational_acronyms(self):
        self.assertEqual(sync_projects.titleize("security-engine"), "Security Engine")
        self.assertEqual(sync_projects.titleize("ci"), "CI")
        self.assertEqual(sync_projects.titleize("p0"), "P0")

    def test_field_lookup_is_case_and_punctuation_insensitive(self):
        project = {
            "fields": {
                "nodes": [
                    {"__typename": "ProjectV2Field", "id": "F1", "name": "Work-Type", "dataType": "TEXT"},
                    {"__typename": "ProjectV2Field", "id": "F2", "name": "AREA", "dataType": "TEXT"},
                ]
            }
        }
        self.assertEqual(sync_projects.find_field(project, ["Work Type"])["id"], "F1")
        self.assertEqual(sync_projects.find_field(project, ["Areas", "Area"])["id"], "F2")

    def test_single_select_uses_aliases(self):
        field = {
            "__typename": "ProjectV2SingleSelectField",
            "id": "STATUS",
            "name": "Status",
            "options": [
                {"id": "TODO", "name": "Todo"},
                {"id": "DONE", "name": "Done"},
            ],
        }
        value, unmatched = sync_projects.desired_field_value(
            field, "status", ["planned"], CONFIG
        )
        self.assertEqual(value, {"singleSelectOptionId": "TODO"})
        self.assertEqual(unmatched, [])

    def test_multi_select_updates_all_matching_areas(self):
        field = {
            "__typename": "ProjectV2MultiSelectField",
            "id": "AREAS",
            "name": "Areas",
            "multiSelectOptions": [
                {"id": "BACK", "name": "Backend"},
                {"id": "SEC", "name": "Security Engine"},
            ],
        }
        value, unmatched = sync_projects.desired_field_value(
            field, "area", ["backend", "security-engine"], CONFIG
        )
        self.assertEqual(value, {"multiSelectOptionIds": ["BACK", "SEC"]})
        self.assertEqual(unmatched, [])

    def test_text_field_works_without_project_options(self):
        field = {
            "__typename": "ProjectV2Field",
            "id": "PHASE",
            "name": "Phase",
            "dataType": "TEXT",
        }
        value, unmatched = sync_projects.desired_field_value(
            field, "phase", ["2"], CONFIG
        )
        self.assertEqual(value, {"text": "Phase 2"})
        self.assertEqual(unmatched, [])

    def test_load_config_rejects_unknown_version(self):
        bad = dict(CONFIG)
        bad["version"] = 2
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "config.json"
            path.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(sync_projects.ProjectSyncError):
                sync_projects.load_config(path)


if __name__ == "__main__":
    unittest.main()
