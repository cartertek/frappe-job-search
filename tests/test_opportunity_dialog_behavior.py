"""Regression checks for Activity Add Row focus and rejection-scope translation."""

import unittest
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1]
          / 'job_search/job_search/doctype/opportunity/opportunity.js')


class OpportunityDialogBehavior(unittest.TestCase):
    def test_rejection_choices_are_converted_to_api_scopes(self):
        script = SOURCE.read_text()
        for option, api_value in (
            ('Search Only', 'search'),
            ('Opportunity Globally', 'opportunity'),
            ('Entire Organization', 'organization'),
        ):
            self.assertIn(f"'{option}':'{api_value}'", script)
        self.assertIn("action === 'reject'", script)
        self.assertIn('scope:scopeValues[values.scope] || values.scope', script)
        self.assertIn('await run(action,args)', script)

    def test_add_row_focuses_required_type_not_date(self):
        script = SOURCE.read_text()
        self.assertIn('activity_log_add(frm, cdt, cdn)', script)
        self.assertIn('grid_rows_by_docname?.[cdn]', script)
        self.assertIn('[data-fieldname="type"] select:visible', script)
        self.assertIn(".trigger('focus')", script)
        # Frappe focuses the first field in set_focus_on_row after 100ms.
        self.assertIn('}, 180)', script)


if __name__ == '__main__':
    unittest.main()
