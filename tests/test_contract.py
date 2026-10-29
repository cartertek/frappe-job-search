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
    "Job Search Opportunity",
    "Job Search Employer",
    "Job Search Task",
    "Job Search Search",
    "Job Search Membership",
    "Job Search Heuristic",
    "Job Search Heuristic Value",
}
CHILD = {
    "Job Search Heuristic",
    "Job Search Research Source",
    "Job Search Procedure Step",
    "Job Search Execution Step",
    "Job Search Interview Contact",
    "Job Search Membership",
    "Job Search Heuristic Value",
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

    def test_job_form_uses_five_part_layout_without_losing_data_fields(self):
        data = json.loads((BASE / "job_search_opportunity" / "job_search_opportunity.json").read_text())
        fields = data["fields"]
        by_name = {field["fieldname"]: field for field in fields}
        names = data["field_order"]
        self.assertEqual(names, [f["fieldname"] for f in fields])
        self.assertEqual(
            [f["fieldname"] for f in fields if f["fieldtype"] == "Section Break"],
            [
                "overview_section",
                "search_fields_section",
                "job_details_section",
                "research_heuristics_section",
                "research_notes_section",
            ],
        )
        self.assertEqual(
            [(f["fieldname"], f.get("label")) for f in fields if f["fieldtype"] == "Column Break"],
            [
                ("overview_column", "Overview"),
                ("metadata_column", "Metadata"),
                ("search_compensation_column", None),
            ],
        )
        self.assertNotIn("overview_job_title", by_name)
        self.assertEqual(by_name["job_title"]["fieldtype"], "Data")
        self.assertTrue(by_name["research_notes_section"]["collapsible"])
        groups = {
            "overview_column": {
                "status",
                "organization",
                "job_title",
                "rejection_scope",
                "rejection_search",
                "rejection_reason",
            },
            "metadata_column": {
                "posting_url",
                "requisition_id",
                "priority",
                "discovered_on",
                "deadline",
                "applied_on",
                "next_action_on",
                "closure_reason",
                "offer_details",
                "latest_posting",
                "last_decision",
                "last_decision_record",
                "latest_application",
                "interview_schedule",
                "globally_rejected",
            },
            "search_fields_section": {
                "active_job_search",
                "location",
                "employment_type",
                "work_arrangement",
                "seniority",
                "compensation_not_given",
                "compensation_min",
                "compensation_max",
                "currency",
                "compensation_period",
                "posted_on",
            },
            "job_details_section": {"job_description"},
            "research_heuristics_section": {"research_heuristics"},
            "research_notes_section": {
                "research_findings",
                "research_recommendation",
                "application_materials_for_review",
                "interview_preparation",
                "human_feedback_and_instructions",
            },
        }

        def slice_between(start, end):
            return fields[names.index(start) + 1 : names.index(end)]

        self.assertEqual(
            {f["fieldname"] for f in slice_between("overview_column", "metadata_column")},
            groups["overview_column"],
        )
        self.assertEqual(
            {f["fieldname"] for f in slice_between("metadata_column", "search_fields_section")},
            groups["metadata_column"],
        )
        self.assertEqual(
            {
                f["fieldname"]
                for f in slice_between("search_fields_section", "job_details_section")
                if f["fieldtype"] != "Column Break"
            },
            groups["search_fields_section"],
        )
        self.assertEqual(
            {f["fieldname"] for f in slice_between("job_details_section", "research_heuristics_section")},
            groups["job_details_section"],
        )
        self.assertEqual(
            {f["fieldname"] for f in slice_between("research_heuristics_section", "research_notes_section")},
            groups["research_heuristics_section"],
        )
        self.assertEqual(
            {f["fieldname"] for f in fields[names.index("research_notes_section") + 1 :]},
            groups["research_notes_section"],
        )
        self.assertEqual(38, len([f for f in fields if f["fieldname"] in set().union(*groups.values())
                                 and f["fieldname"] != "research_heuristics"]))
        js = (BASE / "job_search_opportunity/job_search_opportunity.js").read_text()
        css = (BASE / "job_search_opportunity/job_search_opportunity.css").read_text()
        self.assertNotIn("render_overview_title", js)
        self.assertIn('data-fieldname="metadata_column"', css)
        self.assertIn("grid-template-columns", css)
        self.assertIn(".job-value-record", css)
        self.assertIn("grid-template-columns", css)
        self.assertIn("white-space: pre-wrap", css)
        self.assertIn('"research_heuristics": "templates/includes/job_heuristic_value_row.html"',
                      (BASE / "job_search_opportunity/job_search_opportunity.py").read_text())
        template = (APP / "templates/includes/job_heuristic_value_row.html").read_text()
        self.assertIn("frappe.utils.escape_html(doc.quote", template)
        self.assertIn('__("Heuristic")', template)
        self.assertIn('__("Exact Quote")', template)
        self.assertIn('__("Reasoning")', template)
        self.assertIn('__("Source Date")', template)
        self.assertIn("frappe.utils.escape_html(doc.reasoning", template)
        self.assertIn("frappe.utils.escape_html(doc.source_date", template)
        self.assertNotIn("sync_research_heuristics(frm);\n    if", js)
        setup = (APP / "setup/__init__.py").read_text()
        self.assertIn('frappe.client_cache.delete_value("doctype_form_meta::Job Search Opportunity")', setup)

    def test_job_status_colors_match_form_and_list(self):
        form = (BASE / "job_search_opportunity/job_search_opportunity.js").read_text()
        listing = (BASE / "job_search_opportunity/job_search_opportunity_list.js").read_text()
        colors = {
            "Discovered": "gray", "Researching": "yellow", "Ready to Review": "blue",
            "Qualified": "green", "Applied": "gray", "Interviewing": "green",
            "Accepted": "gray", "Rejected": "red",
        }
        for status, color in colors.items():
            entry = f"'{status}': '{color}'" if ' ' in status else f"{status}: '{color}'"
            with self.subTest(status=status):
                self.assertIn(entry, form)
                self.assertIn(entry, listing)

    def test_review_heuristics_child_table_and_transition_contract(self):
        data = json.loads((BASE / "job_search_opportunity" / "job_search_opportunity.json").read_text())
        fields = {f["fieldname"]: f for f in data["fields"]}
        self.assertEqual(
            (fields["active_job_search"]["fieldtype"], fields["active_job_search"]["options"]),
            ("Link", "Job Search Search"),
        )
        self.assertEqual(
            (fields["research_heuristics"]["fieldtype"], fields["research_heuristics"]["options"]),
            ("Table", "Job Search Heuristic Value"),
        )
        self.assertLess(
            data["field_order"].index("job_details_section"),
            data["field_order"].index("research_heuristics_section"),
        )
        self.assertLess(
            data["field_order"].index("research_heuristics_section"),
            data["field_order"].index("research_notes_section"),
        )
        child = json.loads((BASE / "job_search_heuristic_value/job_search_heuristic_value.json").read_text())
        self.assertEqual(
            child["field_order"],
            [
                "heuristic_id",
                "heuristic_name",
                "quote",
                "reasoning",
                "source",
                "source_date",
            ],
        )
        self.assertEqual(
            {f["fieldname"] for f in child["fields"] if f.get("in_list_view")},
            {"heuristic_name", "quote", "reasoning", "source", "source_date"},
        )
        claim_fields = {f["fieldname"]: f for f in child["fields"]}
        for field in ("reasoning", "source_date"):
            self.assertEqual(1, claim_fields[field]["reqd"])
            self.assertEqual(
                "Data" if field == "source_date" else "Small Text", claim_fields[field]["fieldtype"]
            )
        self.assertIn("YYYY-MM-DD", claim_fields["source_date"]["description"])
        self.assertIn("literal None", claim_fields["source_date"]["description"])
        js = (BASE / "job_search_opportunity/job_search_opportunity.js").read_text()
        self.assertIn("active_job_search(frm)", js)
        self.assertIn("frappe.db.get_doc('Job Search Search', search_name)", js)
        self.assertIn("frappe.model.set_value(cdt,cdn,'heuristic_id',definition.name)", js)
        self.assertIn('Load Heuristic Choices', js)
        workflow = (APP / "workflow.py").read_text()
        self.assertIn('if next_stage == "Ready to Review":', workflow)
        self.assertIn('_review_readiness_failures(deal)', workflow)

    def test_opportunity_has_single_unprefixed_status(self):
        import json

        data = json.loads((BASE / "job_search_opportunity" / "job_search_opportunity.json").read_text())
        fields = {field["fieldname"]: field for field in data["fields"]}
        self.assertNotIn("js_stage", fields)
        self.assertEqual("Status", fields["status"]["label"])
        workflow = (APP / "workflow.py").read_text()
        self.assertNotIn("JS: ", workflow)
        self.assertNotIn("JS: ", workflow)

    def test_simplified_status_actions(self):
        import json

        data = json.loads((BASE / "job_search_opportunity" / "job_search_opportunity.json").read_text())
        status = next(f for f in data["fields"] if f["fieldname"] == "status")
        self.assertEqual(status["options"].splitlines(), [
            "Discovered", "Researching", "Ready to Review", "Qualified",
            "Applied", "Interviewing", "Accepted", "Rejected",
        ])
        self.assertTrue(status["read_only"])
        ui = (BASE / "job_search_opportunity" / "job_search_opportunity.js").read_text()
        for action in ("Mark Qualified", "Needs Research", "Mark Applied",
                       "Begin Interviewing", "Accept Offer", "More Actions"):
            self.assertIn(action, ui)

    def test_no_duplicate_owner_or_qualification(self):
        import json

        data = json.loads((BASE / "job_search_opportunity" / "job_search_opportunity.json").read_text())
        field_names = {f["fieldname"] for f in data["fields"]}
        self.assertTrue({"status", "latest_posting"}.issubset(field_names))
        self.assertFalse({"deal_owner", "qualification", "qualification_rationale"} & field_names)
        workflow = (APP / "workflow.py").read_text()
        self.assertIn('require_decision(deal.name, "Pursue"', workflow)
        self.assertNotIn('deal.qualification', workflow)
        tasks = (APP / "tasks.py").read_text()
        self.assertNotIn('deal.deal_owner', tasks)

    def test_no_duplicate_review_or_posting_fields(self):
        import json

        schema = json.loads((BASE / "job_search_opportunity" / "job_search_opportunity.json").read_text())
        fields = {f["fieldname"] for f in schema["fields"]}
        obsolete = {"review_request", "review_status", "review_assigned_to", "review_task",
                    "review_assignment", "human_action", "human_action_rationale", "posting_text"}
        self.assertFalse(fields & obsolete)
        self.assertIn("latest_posting", fields)
        self.assertEqual("Job Posting", next(f["label"] for f in schema["fields"]
                         if f["fieldname"] == "latest_posting"))

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
