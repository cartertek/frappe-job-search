"""Regression contracts: sort/filterable Applied On and most common Contact."""
import json
import unittest
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]


class DerivedActivityFields(unittest.TestCase):
    def test_read_only_applied_date_is_native_list_sortable(self):
        schema=json.loads((BASE/'job_search/job_search/doctype/opportunity/opportunity.json').read_text())
        fields={f['fieldname']:f for f in schema['fields']}
        for name,kind in (('applied_on','Date'),('common_contact','Data')):
            with self.subTest(name=name):
                f=fields[name]
                self.assertEqual(f['fieldtype'],kind)
                for property_name in ('read_only','in_list_view','in_standard_filter','search_index'):
                    self.assertEqual(f[property_name],1)

    def test_derived_values_replace_old_one_time_application_dates(self):
        workflow=(BASE/'job_search/workflow.py').read_text()
        self.assertIn('max(application_dates) if application_dates else None',workflow)
        self.assertIn('contact_counts = Counter(',workflow)
        self.assertIn('(-contact_counts[name], name)',workflow)
        self.assertNotIn('if status == "Applied" and not doc.applied_on:',workflow)
        service=(BASE/'job_search/services.py').read_text()
        self.assertNotIn('deal.applied_on = submitted_on',service)
        application=(BASE/'job_search/job_search/doctype/job_search_application/job_search_application.py').read_text()
        self.assertNotIn('def after_insert(self):',application)

    def test_triggers_recompute_both_fields_for_each_activity_change(self):
        source=(BASE/'job_search/applied_sync.py').read_text()
        for term in ('MAX(activity.date)','opportunity.applied_on',
                     'opportunity.common_contact','ORDER BY COUNT(*) DESC',
                     'NOT (OLD.date <=> NEW.date)','NOT (OLD.contact <=> NEW.contact)',
                     'AFTER INSERT','AFTER UPDATE','AFTER DELETE',
                     'NEW.parent','OLD.parent','sync_all_applied()'):
            self.assertIn(term,source)


if __name__=='__main__':
    unittest.main()
