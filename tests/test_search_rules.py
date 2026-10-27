"""Matching semantics independent of Frappe database or UI."""

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def obj(**kwargs):
    fields = dict(job_title='Python Engineer', location='Portland, OR',
                  employment_type='Full Time', work_arrangement='Remote',
                  seniority='Senior', posted_on='2026-10-01', compensation_min=130000,
                  currency='USD', compensation_period='Year')
    fields.update(kwargs)
    return types.SimpleNamespace(**fields)


def search(**kwargs):
    fields = dict(title_matches='Python Engineer', location_match='Portland, OR',
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
        for change in [dict(job_title='Designer'), dict(location='Austin'),
                       dict(employment_type='Contract'), dict(work_arrangement='Hybrid'),
                       dict(seniority='Junior'), dict(posted_on=None),
                       dict(compensation_min=None), dict(compensation_min=115000),
                       dict(currency='EUR'), dict(compensation_period='Hour')]:
            with self.subTest(change=change):
                self.assertFalse(self.module.matches(obj(**change), search()))

    def test_exact_title_and_location(self):
        self.assertTrue(self.module.matches(obj(), search()))
        self.assertFalse(self.module.matches(obj(job_title='Senior Python Engineer'), search()))
        self.assertFalse(self.module.matches(obj(location='Portland, OR, USA'), search()))
        self.assertTrue(self.module.matches(
            obj(job_title='PYTHON ENGINEER', location=' portland, or '), search()
        ))

    def test_multiple_titles_match_any_full_title(self):
        criteria = search(title_matches='Frontend Developer\nPython Engineer\nSoftware Engineer')
        self.assertTrue(self.module.matches(obj(), criteria))
        self.assertTrue(self.module.matches(obj(job_title='Software Engineer'), criteria))
        self.assertFalse(self.module.matches(obj(job_title='Senior Software Engineer'), criteria))
        self.assertTrue(self.module.matches(obj(), search(title_matches='\n  Python Engineer  \n\n')))

    def test_no_filters(self):
        self.assertTrue(self.module.matches(obj(), search(**{k:None for k in vars(search())})))

    def test_global_and_explicit_precedence(self):
        from types import SimpleNamespace as NS
        module = self.module
        jobs = [dict(vars(obj()), name='a', organization='one', globally_rejected=0, status='Discovered'),
                dict(vars(obj(job_title='Designer')), name='b', organization='one',
                     globally_rejected=0, status='Discovered'),
                dict(vars(obj()), name='c', organization='two', globally_rejected=1, status='Discovered'),
                dict(vars(obj()), name='d', organization='blocked',
                     globally_rejected=0, status='Discovered')]
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
