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
    "Job Search Decision", "Job Search Transition", "Job Search Opportunity",
    "Job Search Employer", "Job Search Task", "Job Search Search", "Job Search Membership",
}
CHILD = {"Job Search Research Source", "Job Search Procedure Step",
         "Job Search Execution Step", "Job Search Interview Contact", "Job Search Membership"}


class SchemaTest(unittest.TestCase):
    def test_all_schemas_valid_and_scoped(self):
        found = set()
        for path in sorted(BASE.glob("*/*.json")):
            data = json.loads(path.read_text())
            name = data["name"]
            found.add(name)
            self.assertEqual("Job Search", data["module"])
            self.assertEqual("DocType", data["doctype"])
            if name not in CHILD:
                self.assertIn(data["autoname"], ("JS-.YYYY.-.#####", "hash"))
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

    def test_no_crm_model_links(self):
        for path in BASE.glob("*/*.json"):
            data = json.loads(path.read_text())
            for f in data["fields"]:
                self.assertNotIn(f.get("options"), {"CRM Deal", "CRM Organization", "CRM Task"})

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
            "get_opportunity_context", "publish_human_review", "get_human_action_queue",
            "get_company_dossier", "authorize_decision", "get_search_results",
            "set_search_membership", "reject_job", "reject_organization",
        })

    def test_global_display_names_are_consistent(self):
        import csv

        translations = APP / "translations" / "en.csv"
        with translations.open(newline="") as f:
            labels = dict(csv.reader(f))
        from ast import literal_eval

        setup = (APP / "setup" / "__init__.py").read_text()
        block = setup.split("WORKSPACE_LABELS = ", 1)[1].split('\n\ndef ensure_workspace', 1)[0]
        self.assertEqual(labels, literal_eval(block))
        self.assertIn("clear_translation_cache()", setup)

    def test_opportunity_has_single_unprefixed_status(self):
        import json

        data = json.loads((BASE / "job_search_opportunity" / "job_search_opportunity.json").read_text())
        fields = {field["fieldname"]: field for field in data["fields"]}
        self.assertNotIn("js_stage", fields)
        self.assertEqual("Status", fields["status"]["label"])
        workflow = (APP / "workflow.py").read_text()
        self.assertNotIn("JS: ", workflow)
        self.assertNotIn("JS: ", workflow)

    def test_standalone_ui(self):
        hooks = (APP / "hooks.py").read_text()
        self.assertNotIn('required_apps = ["crm"]', hooks)
        self.assertIn('"Job Search Opportunity"', hooks)
        self.assertIn('add_to_apps_screen = [', hooks)
        self.assertIn('"route": app_home', hooks)
        self.assertIn('"has_permission": "job_search.permissions.can_access_app"', hooks)
        self.assertTrue((APP / "public" / "images" / "job-search.svg").exists())
        self.assertTrue((BASE / "job_search_opportunity" / "job_search_opportunity.js").exists())
        self.assertTrue((APP / "migration.py").exists())

    def test_no_untracked_direct_crm_mutation(self):
        source = (APP / "services.py").read_text() + (APP / "api.py").read_text()
        self.assertNotIn("frappe.db.set_value(", source)
        self.assertNotIn("ignore_permissions=True", source)


if __name__ == "__main__":
    unittest.main()
