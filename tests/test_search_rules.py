"""Matching semantics independent of Frappe database or UI."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def obj(**kwargs):
    fields = dict(js_job_title='Python Engineer', js_location='Portland, OR',
                  js_employment_type='Full Time', js_work_arrangement='Remote',
                  js_seniority='Senior', js_posted_on='2026-10-01', js_compensation_min=130000,
                  js_currency='USD', js_compensation_period='Year')
    fields.update(kwargs)
    return types.SimpleNamespace(**fields)


def search(**kwargs):
    fields = dict(title_contains='Python', location_contains='Portland',
                  employment_type='Full Time', work_arrangement='Remote',
                  seniority='Senior', posted_after='2026-09-01', salary_min=120000,
                  currency='USD', compensation_period='Year')
    fields.update(kwargs)
    return types.SimpleNamespace(**fields)


class SearchRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fake = types.ModuleType('frappe')
        fake.utils = types.ModuleType('frappe.utils')
        from datetime import date
        fake.utils.getdate = lambda x: date.fromisoformat(str(x))
        sys.modules['frappe'] = fake
        sys.modules['frappe.utils'] = fake.utils
        perms = types.ModuleType('job_search.permissions')
        perms.require_doc = lambda *args: None
        perms.require_operator = lambda: None
        sys.modules['job_search.permissions'] = perms
        spec = importlib.util.spec_from_file_location(
            'standalone_search_rules', ROOT / 'job_search/searches.py'
        )
        cls.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.module)

    def test_deterministic_all_filters(self):
        self.assertTrue(self.module.matches(obj(), search()))
        for change in [dict(js_job_title='Designer'), dict(js_location='Austin'),
                       dict(js_employment_type='Contract'), dict(js_work_arrangement='Hybrid'),
                       dict(js_seniority='Junior'), dict(js_posted_on=None),
                       dict(js_compensation_min=None), dict(js_compensation_min=115000),
                       dict(js_currency='EUR'), dict(js_compensation_period='Hour')]:
            with self.subTest(change=change):
                self.assertFalse(self.module.matches(obj(**change), search()))

    def test_no_filters(self):
        self.assertTrue(self.module.matches(obj(), search(**{k:None for k in vars(search())})))

    def test_global_and_explicit_precedence(self):
        from types import SimpleNamespace as NS
        module = self.module
        jobs = [dict(vars(obj()), name='a', organization='one', globally_rejected=0, js_stage='Discovered'),
                dict(vars(obj(js_job_title='Designer')), name='b', organization='one',
                     globally_rejected=0, js_stage='Discovered'),
                dict(vars(obj()), name='c', organization='two', globally_rejected=1, js_stage='Discovered'),
                dict(vars(obj()), name='d', organization='blocked',
                     globally_rejected=0, js_stage='Discovered')]
        class Row(dict):
            __getattr__ = dict.get
        dataset = [Row(x) for x in jobs]
        overrides = [NS(job=key, override=action) for key, action in (
            ('a', 'Exclude'), ('b', 'Include'), ('c', 'Include'), ('d', 'Include')
        )]
        active = search(require_heuristics=0, overrides=overrides)
        fake = sys.modules['frappe']
        fake.get_list = lambda *args, **kwargs: dataset
        fake.db = NS(get_value=lambda dt, org, field: org=='blocked')
        with patch.object(module, 'require_doc', return_value=active):
            self.assertEqual(['b'], [x['name'] for x in module.matching_jobs('search')])
            active.require_heuristics = 1
            self.assertEqual(['b'], [x['name'] for x in module.matching_jobs('search')])
            active.overrides = []
            self.assertEqual([], module.matching_jobs('search'))
            active.require_heuristics = 0
            self.assertEqual(['a'], [x['name'] for x in module.matching_jobs('search')])


if __name__ == '__main__':
    unittest.main()
