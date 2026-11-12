"""Issue #18: Activity Log layout and transition guards, including direct REST writes."""

import json
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
DT = BASE / 'job_search/job_search/doctype'


class OpportunityActivityTests(unittest.TestCase):
    def test_child_schema_matches_issue_18(self):
        schema = json.loads((DT/'opportunity_activity/opportunity_activity.json').read_text())
        self.assertEqual(schema['istable'], 1)
        self.assertEqual(schema['field_order'], ['date','type','contact','platform','notes'])
        fields = {item['fieldname']:item for item in schema['fields']}
        self.assertEqual(fields['date']['default'],'Today')
        self.assertTrue(fields['date']['reqd'])
        self.assertEqual(fields['type']['options'].splitlines(), [
            '', 'Message','Application','Interview','Offer','Rejection','Acceptation','Note',
        ])
        self.assertEqual(fields['type'].get('default'), '')
        self.assertTrue(fields['type']['reqd'])
        for name in ('contact','platform','notes'):
            self.assertFalse(fields[name].get('reqd', 0))

    def test_opportunity_has_activity_table_and_no_jobs_description(self):
        schema=json.loads((DT/'opportunity/opportunity.json').read_text())
        fields={f['fieldname']:f for f in schema['fields']}
        self.assertEqual(fields['activity_log']['options'],'Opportunity Activity')
        self.assertEqual(fields['activity_log']['fieldtype'],'Table')
        self.assertNotIn('description',fields['jobs'])

    def test_rejection_activity_and_chronological_order_are_enforced(self):
        opportunities=(BASE/'job_search/opportunities.py').read_text()
        actions=(BASE/'job_search/workflow_actions.py').read_text()
        workflow=(BASE/'job_search/workflow.py').read_text()
        js=(DT/'opportunity/opportunity.js').read_text()
        self.assertIn("row.type == 'Rejection'",opportunities)
        self.assertIn("'date': nowdate(), 'type': 'Rejection', 'notes': reason.strip()", opportunities)
        self.assertIn('ensure_rejection_activity(job, rationale)',actions)
        self.assertIn('newly_rejected',opportunities)
        self.assertIn('ensure_rejection_activity(',opportunities)
        self.assertIn("sorted(doc.activity_log, key=lambda row: str(row.date or ''))",workflow)
        self.assertIn('row.idx = index',workflow)
        self.assertIn("String(a.date || '').localeCompare(String(b.date || ''))",js)

    def test_dialog_only_for_missing_activity_and_default_today(self):
        source=(DT/'opportunity/opportunity.js').read_text()
        self.assertIn("mark_applied:'Application'",source)
        self.assertIn("begin_interviewing:'Interview'",source)
        self.assertIn("accept_offer:'Acceptation'",source)
        self.assertIn('frappe.datetime.get_today()',source)
        self.assertIn('(frm.doc.activity_log || []).some(row=>row.type===type)',source)
        self.assertIn('if (exists && !otherFields.length) return run(action)',source)
        self.assertIn('const fields=exists ? otherFields : [...activityFields,...otherFields]',source)
        self.assertIn('activityAction(\'Accept Offer\'',source)

    def test_transitions_require_existing_or_atomic_activity(self):
        workflow=(BASE/'job_search/workflow.py').read_text()
        cases = [('Applied','Application'), ('Interviewing','Interview'), ('Accepted','Acceptation')]
        for target,activity in cases:
            self.assertIn(f'"{target}": "{activity}"',workflow)
        self.assertIn('row.type == required_activity for row in deal.activity_log',workflow)
        action=(BASE/'job_search/workflow_actions.py').read_text()
        self.assertIn('job.append("activity_log", {',action)
        self.assertIn('job.status = target\n    job.save()',action)
        self.assertIn('if not isinstance(activity, dict):',action)
        self.assertIn('getdate(date)',action)
        self.assertIn('"date": date, "type": activity_type',action)
        self.assertIn('The Application activity records Mark Applied',action)
        self.assertNotIn('action == "mark_applied" and job.eligibility_status',action)
        self.assertNotIn('require_decision(deal.name, "Authorize Application"',workflow)
        self.assertIn('require_approver()  # Protect direct ORM / REST',workflow)
        self.assertIn('doc.applied_on = max(dates)',workflow)
        api=(BASE/'job_search/api.py').read_text()
        self.assertIn('offer_details=None, activity=None',api)


if __name__=='__main__':
    unittest.main()
