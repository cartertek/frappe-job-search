"""Pure-Python preflight: runs without an installed Frappe bench."""

import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "job_search"
MODULE = APP / "job_search"
BASE = MODULE / "doctype"
EXPECTED = {
    "Job Search Posting", "Job Search Research", "Job Search Source",
    "Job Search Research Source", "Job Search Procedure", "Job Search Procedure Step",
    "Job Search Procedure Execution", "Job Search Execution Step",
    "Job Search Application", "Job Search Interview", "Job Search Interview Contact",
    "Job Search Decision", "Job Search Transition",
}
CHILD = {"Job Search Research Source", "Job Search Procedure Step",
         "Job Search Execution Step", "Job Search Interview Contact"}


class SchemaTest(unittest.TestCase):
    def test_all_schemas_valid_and_scoped(self):
        found = set()
        for path in sorted(BASE.glob("*/*.json")):
            data = json.loads(path.read_text())
            name = data["name"]
            found.add(name)
            self.assertEqual("Job Search", data["module"])
            self.assertEqual("DocType", data["doctype"])
            self.assertEqual(int(name in CHILD), data["istable"])
            fields = data["fields"]
            names = [f["fieldname"] for f in fields]
            self.assertEqual(names, data["field_order"])
            self.assertEqual(len(names), len(set(names)), name)
            self.assertTrue((path.parent / (path.stem + ".py")).exists())
            for field in fields:
                if field["fieldtype"] in ("Link", "Table"):
                    self.assertTrue(field.get("options"), (name, field))
                if field["fieldtype"] == "Table":
                    self.assertIn(field["options"], CHILD)
            if name not in CHILD:
                self.assertTrue(data["permissions"], name)
        self.assertEqual(EXPECTED, found)

    def test_crm_fields_are_version_controlled_and_namespaced(self):
        fields = json.loads((APP / "fixtures" / "custom_field.json").read_text())
        self.assertGreaterEqual(len(fields), 30)
        self.assertEqual(len(fields), len({f["name"] for f in fields}))
        self.assertEqual({"CRM Deal", "CRM Organization", "CRM Task"}, {f["dt"] for f in fields})
        for field in fields:
            self.assertTrue(field["fieldname"].startswith("js_"))
            self.assertEqual(field["name"], field["dt"] + "-" + field["fieldname"])
            self.assertTrue(field["insert_after"])

    def test_procedure_seed_versions_and_steps(self):
        procedures = json.loads((APP / "setup" / "procedures.json").read_text())
        self.assertEqual(10, len(procedures))
        self.assertEqual(len(procedures), len({(x["procedure_id"], x["version"]) for x in procedures}))
        for p in procedures:
            self.assertEqual("Active", p["status"])
            self.assertTrue(p["steps"])
            self.assertTrue(all(step["required"] for step in p["steps"]))

    def test_all_json_metadata_parses(self):
        for path in APP.rglob("*.json"):
            json.loads(path.read_text())

    def test_operator_api_contract(self):
        tree = ast.parse((APP / "api.py").read_text())
        exposed = {n.name for n in tree.body
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                           and d.func.attr == "whitelist" for d in n.decorator_list)}
        self.assertGreaterEqual(exposed, {
            "register_opportunity", "capture_posting", "add_research", "start_procedure",
            "complete_procedure_step", "complete_procedure", "transition_opportunity",
            "record_application", "record_interview", "create_follow_up",
            "get_work_queue", "get_research_queue", "get_follow_up_queue",
            "get_opportunity_context", "publish_human_review", "get_human_action_queue", "get_company_dossier", "authorize_decision",
        })

    def test_crm_only_ui(self):
        self.assertFalse((APP / "dock").exists())
        self.assertFalse((MODULE / "sidebar").exists())
        self.assertFalse((MODULE / "workspace").exists())
        hooks = (APP / "hooks.py").read_text()
        self.assertNotIn("add_to_apps_screen", hooks)
        self.assertIn('required_apps = ["crm"]', hooks)
        layout = (APP / "setup" / "crm_layout.py").read_text()
        self.assertIn('"Quick Entry"', layout)
        self.assertIn('"Data Fields"', layout)
        self.assertIn('"Side Panel"', layout)
        self.assertIn('"js_is_job_search"', layout)
        self.assertIn('"js_job_title"', layout)

    def test_no_untracked_direct_crm_mutation(self):
        source = (APP / "services.py").read_text() + (APP / "api.py").read_text()
        self.assertNotIn("frappe.db.set_value(", source)
        self.assertNotIn("ignore_permissions=True", source)


if __name__ == "__main__":
    unittest.main()
