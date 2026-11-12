"""The Pursue approval is audited even when no narrative is entered."""
import json
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


class QualificationRationaleContract(unittest.TestCase):
    def test_qualified_action_is_single_click(self):
        source = (BASE / 'job_search/job_search/doctype/opportunity/opportunity.js').read_text()
        self.assertIn("primary('Mark Qualified','qualify');", source)
        self.assertNotIn("primary('Mark Qualified','qualify',reason)", source)

    def test_rationale_optional_for_pursue_only(self):
        decision_path = BASE / 'job_search/job_search/doctype/job_search_decision'
        source = (decision_path / 'job_search_decision.py').read_text()
        self.assertIn('self.decision != "Pursue"', source)
        self.assertIn('self.authorized_by = frappe.session.user', source)
        self.assertIn('self.authorized_at = now_datetime()', source)
        self.assertIn('Decisions are immutable', source)
        fields = json.loads((decision_path / 'job_search_decision.json').read_text())['fields']
        self.assertFalse(next(f for f in fields if f['fieldname'] == 'rationale').get('reqd'))

    def test_server_still_checks_research_and_approver(self):
        source = (BASE / 'job_search/workflow_actions.py').read_text()
        self.assertIn('require_approver()', source)
        self.assertIn('_has_completed_research_procedure(job)', source)
        self.assertIn('_decision(job, "Pursue", rationale)', source)
        self.assertIn('if action == "accept_offer" and not rationale:', source)


if __name__ == '__main__':
    unittest.main()
