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
    "Job Search Posting",
    "Job Search Research",
    "Job Search Source",
    "Job Search Research Source",
    "Job Search Procedure",
    "Job Search Procedure Step",
    "Job Search Procedure Execution",
    "Job Search Execution Step",
    "Job Search Application",
    "Job Search Interview",
    "Job Search Interview Contact",
    "Job Search Decision",
    "Job Search Transition",
    "Opportunity",
    "Job",
    "Opportunity Job",
    "Job Search Employer",
    "Job Search Task",
    "Job Search Search",
    "Job Search Membership",
    "Job Search Heuristic",
    "Job Search Heuristic Value",
    "Research Strategy",
    "Assigned Research Strategy",
    "Opportunity Job",
}
CHILD = {
    "Job Search Heuristic",
    "Job Search Research Source",
    "Job Search Procedure Step",
    "Job Search Execution Step",
    "Job Search Interview Contact",
    "Job Search Membership",
    "Job Search Heuristic Value",
    "Assigned Research Strategy",    "Opportunity Job",

}


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
            "register_opportunity", "register_job", "capture_posting", "add_research", "start_procedure",
            "complete_procedure_step", "complete_procedure", "transition_opportunity",
            "record_application", "record_interview", "create_follow_up",
            "get_work_queue", "get_research_queue", "get_follow_up_queue",
            "get_opportunity_context", "publish_human_review", "get_human_action_queue",
            "get_company_dossier", "authorize_decision", "get_search_results",
            "set_search_membership", "reject_job", "reject_organization",
            "get_search_research_strategies",
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

    def test_job_and_opportunity_own_distinct_lifecycles(self):
        job=json.loads((BASE/'job/job.json').read_text())
        opportunity=json.loads((BASE/'opportunity/opportunity.json').read_text())
        job_fields={f['fieldname']:f for f in job['fields']}
        opp_fields={f['fieldname']:f for f in opportunity['fields']}
        self.assertNotIn('status',job_fields)
        self.assertEqual(job_fields['availability_status']['options'].splitlines(),
                         ['Unknown','Active','Closed','Rejected'])
        self.assertNotIn('availability_status',opp_fields)
        self.assertIn('status',opp_fields)
        self.assertNotIn('research_heuristics',opp_fields)
        self.assertIn('research_heuristics',job_fields)
        self.assertNotIn('job_description',opp_fields)
        self.assertIn('job_description',job_fields)
        self.assertIn('jobs',opp_fields)
        self.assertEqual(opp_fields['jobs']['options'],'Opportunity Job')
        self.assertIn('research_findings',opp_fields)
        self.assertIn('latest_posting',job_fields)
        self.assertNotIn('latest_posting',opp_fields)
        self.assertIn('rejection_scope',opp_fields)
        self.assertNotIn('rejection_scope',job_fields)
        self.assertIn('job_rejection_reason',job_fields)
        self.assertEqual(job['title_field'],'job_title')
        self.assertEqual(opportunity['title_field'],'opportunity_name')

    def test_opportunity_action_and_job_evidence_ui_are_separate(self):
        job_js=(BASE/'job/job.js').read_text()
        opp_js=(BASE/'opportunity/opportunity.js').read_text()
        self.assertIn("frappe.ui.form.on('Job'",job_js)
        self.assertIn('Load Heuristic Choices',job_js)
        self.assertIn('Reject Job',job_js)
        self.assertIn("frappe.ui.form.on('Opportunity'",opp_js)
        for action in ('Begin Research','Ready to Review','Mark Qualified',
                       'Needs Research','Mark Applied','Begin Interviewing','Accept Offer',
                       'Reject Opportunity','Reopen Opportunity'):
            self.assertIn(action,opp_js)
        self.assertNotIn('Mark Applied',job_js)
        self.assertNotIn('Load Heuristic Choices',opp_js)

    def test_memberships_use_opportunities_not_jobs(self):
        child=json.loads((BASE/'job_search_membership/job_search_membership.json').read_text())
        field=next(f for f in child['fields'] if f['fieldname']=='opportunity')
        self.assertEqual(field['options'],'Opportunity')
        search_doc=json.loads((BASE/'job_search_search/job_search_search.json').read_text())
        self.assertEqual(next(f for f in search_doc['fields'] if f['fieldname']=='overrides')['label'],
                         'Explicit Opportunity Overrides')
        opp=json.loads((BASE/'opportunity/opportunity.json').read_text())
        self.assertEqual(next(f for f in opp['fields'] if f['fieldname']=='jobs')['options'],
                         'Opportunity Job')
        member=json.loads((BASE/'opportunity_job/opportunity_job.json').read_text())
        self.assertEqual(member['fields'][0]['options'],'Job')

    def test_documentation_and_migration_references(self):
        hooks=(APP/'hooks.py').read_text()
        self.assertIn('"Opportunity":',hooks)
        self.assertIn('"Job":',hooks)
        patch=(APP/'patches/v5_split_opportunities.py').read_text()
        self.assertIn('rename_doc("DocType", old, new',patch)
        migration=(APP/'opportunity_migration.py').read_text()
        self.assertIn('verify_opportunity_migration()',migration)
        self.assertIn("availability_status='Unknown'",migration)
        self.assertNotIn("THEN 'Rejected'",migration)
        self.assertIn('Job Search Transition',migration)
        self.assertIn('Job Search Decision',migration)

    def test_heuristics_are_named_child_rows(self):
        import json

        search = json.loads((BASE / "job_search_search" / "job_search_search.json").read_text())
        field = next(f for f in search["fields"] if f["fieldname"] == "heuristics")
        self.assertEqual((field["fieldtype"], field["options"]),
                         ("Table", "Job Search Heuristic"))
        heuristic = json.loads((BASE / "job_search_heuristic" / "job_search_heuristic.json").read_text())
        self.assertEqual(heuristic["field_order"], ["heuristic_name", "description"])
        self.assertTrue(all(f["reqd"] for f in heuristic["fields"]))
        setup = (APP / "setup" / "__init__.py").read_text()
        self.assertIn("migrate_heuristics_table()", setup)

    def test_heuristic_template_supports_header_row(self):
        template = (APP / "templates/includes/search_heuristic_row.html").read_text()
        css = (BASE / "job_search_search/job_search_search.css").read_text()
        self.assertIn("{% if (doc) { %}", template)
        self.assertIn("{% } else { %}", template)
        self.assertIn("doc.description", template)
        self.assertIn('__("Name")', template)
        self.assertIn('__("Description")', template)
        self.assertNotIn("<style>", template)
        self.assertIn("grid-template-columns", css)
        self.assertIn('frappe.utils.icon("pencil", "xs")', template)
        self.assertIn(".grid-heading-row .template-row", css)
        self.assertIn("minmax(140px, 24%) minmax(0, 1fr)", css)
        self.assertIn(".template-row-index", css)
        self.assertIn(".template-row", css)
        setup = (APP / "setup/__init__.py").read_text()
        self.assertIn('frappe.cache.delete_value("doctype_form_meta::Job Search Search")', setup)

    def test_standalone_ui(self):
        hooks = (APP / "hooks.py").read_text()
        self.assertNotIn('required_apps = ["crm"]', hooks)
        self.assertIn('"Opportunity"', hooks)
        self.assertIn('add_to_apps_screen = [', hooks)
        self.assertIn('"route": app_home', hooks)
        self.assertIn('"has_permission": "job_search.permissions.can_access_app"', hooks)
        self.assertTrue((APP / "public" / "images" / "job-search.svg").exists())
        self.assertTrue((BASE / "opportunity" / "opportunity.js").exists())
        self.assertTrue((APP / "migration.py").exists())

    def test_no_untracked_direct_crm_mutation(self):
        source = (APP / "services.py").read_text() + (APP / "api.py").read_text()
        self.assertNotIn("frappe.db.set_value(", source)
        self.assertNotIn("ignore_permissions=True", source)


if __name__ == "__main__":
    unittest.main()
