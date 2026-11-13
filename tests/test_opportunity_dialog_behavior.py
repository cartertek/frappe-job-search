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

    def test_add_row_uses_native_frappe_focus_on_required_type(self):
        import json

        base = SOURCE.parent.parent / 'opportunity_activity' / 'opportunity_activity.json'
        schema = json.loads(base.read_text())
        self.assertEqual(schema['field_order'][0], 'type')
        self.assertEqual(schema['fields'][0]['fieldname'], 'type')
        fields = {field['fieldname']: field for field in schema['fields']}
        self.assertTrue(fields['type']['reqd'])
        self.assertTrue(fields['type']['options'].startswith('\n'))
        self.assertEqual(fields['type']['default'], '')
        self.assertEqual(fields['date']['default'], 'Today')
        # No async event that executes before the row exists and gets overridden
        # by Frappe's built-in grid.set_focus_on_row().
        script = SOURCE.read_text()
        self.assertNotIn('activity_log_add(', script)
        self.assertNotIn('grid_rows_by_docname?.[cdn]', script)


if __name__ == '__main__':
    unittest.main()
