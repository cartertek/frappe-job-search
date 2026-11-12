"""Issue #15 follow-up: migration safety and friendly user messages."""
import ast
import json
import unittest
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]


class OpportunityFollowupContract(unittest.TestCase):
    def test_active_job_search_is_only_on_opportunity(self):
        job=json.loads((BASE/'job_search/job_search/doctype/job/job.json').read_text())
        opportunity=json.loads((BASE/'job_search/job_search/doctype/opportunity/opportunity.json').read_text())
        self.assertNotIn('active_job_search',job['field_order'])
        field=next(f for f in opportunity['fields'] if f['fieldname']=='active_job_search')
        self.assertEqual(field['label'],'Active Job Search')
        job_js=(BASE/'job_search/job_search/doctype/job/job.js').read_text()
        self.assertIn('get_job_active_searches',job_js)

    def test_consolidation_fails_closed_and_preserves_historical_records(self):
        source=(BASE/'job_search/opportunity_cleanup.py').read_text()
        for invariant in ('Opportunity Consolidation','source_snapshot','_compatible',
                          'distinct hiring efforts','verify_opportunity_migration',
                          'job_search:opportunity_cleanup_v6','DocTags',
                          "'Job Search Transition'", "'Job Search Task'", "'Job Search Posting'"):
            self.assertIn(invariant,source)
        self.assertIn('frappe.db.delete(\'Opportunity\'',source)
        self.assertIn('frappe.db.set_default(MARKER',source)
        self.assertIn('reconcile_opportunities_v6()',(BASE/'job_search/setup/__init__.py').read_text())

    def test_friendly_names_are_used_in_errors_and_dialogs(self):
        helper=(BASE/'job_search/display.py').read_text()
        self.assertIn("get_value('Job', name, 'job_title')",helper)
        self.assertIn("get_value('Opportunity', name, 'opportunity_name')",helper)
        workflow=(BASE/'job_search/workflow.py').read_text()
        self.assertIn('job_label(job)',workflow)
        self.assertIn('job_label(row.job)',workflow)
        for form,field in (('job/job.js','job_title'),('opportunity/opportunity.js','opportunity_name')):
            source=(BASE/'job_search/job_search/doctype'/form).read_text()
            self.assertIn(f'frm.doc.{field}',source)
            self.assertIn('Could not update',source)
        search_ui=(BASE/'job_search/job_search/doctype/job_search_search/job_search_search.js').read_text()
        self.assertIn('qualifying_job_labels',search_ui)
        self.assertIn('organization_name',search_ui)

    def test_mixed_preapproval_stages_are_resolved_conservatively(self):
        code=(BASE/'job_search/opportunity_cleanup.py').read_text()
        ast.parse(code)
        self.assertIn("{'Discovered', 'Researching', 'Ready to Review'}",code)
        self.assertIn("target.status = 'Researching'",code)
        self.assertIn('Consolidated historical pursuit statuses',code)
        self.assertIn('last_decision_record',code)

    def test_archive_is_operator_read_only(self):
        archived=json.loads((BASE/'job_search/job_search/doctype/opportunity_consolidation/opportunity_consolidation.json').read_text())
        self.assertTrue(archived['read_only'])
        self.assertEqual(archived['name'],'Opportunity Consolidation')
        self.assertTrue(all(
            p.get('read') and not p.get('write') and not p.get('delete')
            for p in archived['permissions']
        ))

if __name__=='__main__':
    unittest.main()
