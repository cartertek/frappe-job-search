"""Issue #25: persist a filterable field driven solely by Application activities."""

import json
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]


class DerivedAppliedContract(unittest.TestCase):
    def test_applied_is_a_read_only_check_visible_in_lists_and_filters(self):
        schema = json.loads((BASE/'job_search/job_search/doctype/opportunity/opportunity.json').read_text())
        field = next(f for f in schema['fields'] if f['fieldname'] == 'applied')
        self.assertEqual(field['fieldtype'], 'Check')
        self.assertEqual(field['default'], '0')
        self.assertEqual(field['read_only'], 1)
        self.assertEqual(field['in_list_view'], 1)
        self.assertEqual(field['in_standard_filter'], 1)
        self.assertEqual(field['search_index'], 1)

    def test_every_activity_write_path_is_covered_at_database_level(self):
        source = (BASE/'job_search/applied_sync.py').read_text()
        for operation in ('AFTER INSERT', 'AFTER UPDATE', 'AFTER DELETE'):
            self.assertIn(operation, source)
        self.assertIn("type = 'Application'", source)
        self.assertIn("parenttype = 'Opportunity'", source)
        self.assertIn("parentfield = 'activity_log'", source)
        self.assertIn('OLD.parent', source)
        self.assertIn('NEW.parent', source)
        self.assertIn('EXISTS (', source)
        self.assertIn('sql_ddl(', source)
        self.assertIn('sync_all_applied()', source)
        self.assertIn('drop_applied_triggers()', source)
        # Backfill and trigger installation is idempotent on normal migrations.
        setup = (BASE/'job_search/setup/__init__.py').read_text()
        self.assertIn('ensure_applied_sync()', setup)
        hooks = (BASE/'job_search/hooks.py').read_text()
        self.assertIn('before_uninstall = "job_search.applied_sync.drop_applied_triggers"', hooks)

    def test_parent_save_refreshes_derived_field_without_latency(self):
        source = (BASE/'job_search/workflow.py').read_text()
        self.assertIn('doc.applied = 1 if any(row.type == "Application"', source)
        self.assertIn('else 0', source)


if __name__ == '__main__':
    unittest.main()
