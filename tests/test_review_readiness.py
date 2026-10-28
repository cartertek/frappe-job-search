"""Pure-Python behavior tests for the Job Search #7 review transition gate."""

import importlib.util
import sys
import types
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / 'job_search'


def record(**fields):
    return types.SimpleNamespace(**fields)


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, APP / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReviewReadiness(unittest.TestCase):
    def setUp(self):
        self.fake = types.ModuleType('frappe')
        self.fake.throw = lambda text: (_ for _ in ()).throw(ValueError(text))
        self.fake.flags = record(job_search_transition_context=None)
        self.fake.utils = types.ModuleType('frappe.utils')
        self.fake.utils.now_datetime = lambda: '2026-10-27 20:00:00'
        self.fake.utils.getdate = lambda value: date.fromisoformat(str(value)[:10])
        self.fake.db = record(exists=lambda *a: True, get_value=lambda *a, **k: False)
        self.search = record(name='SEARCH1', enabled=1,
            title_matches='Python Engineer', location_match='Portland, OR',
            employment_type='Full Time', work_arrangement='Remote', seniority='Senior',
            posted_after='2026-09-01', salary_min=120000, currency='USD',
            compensation_period='Year', require_heuristics=0, overrides=[],
            heuristics=[record(name='H1', heuristic_name='Personal contact'),
                        record(name='H2', heuristic_name='Hiring evidence')])
        self.job = record(name='JOB1', organization='Employer', job_title='Python Engineer',
            location='Portland, OR', employment_type='Full Time', work_arrangement='Remote',
            seniority='Senior', posted_on='2026-10-01', compensation_min=130000,
            currency='USD', compensation_period='Year', active_job_search='SEARCH1',
            globally_rejected=0, research_heuristics=[
                record(heuristic_id='builtin:job-title', heuristic_name='Job Title', value='The description matches the role'),
                record(heuristic_id='H1', heuristic_name='Personal contact', value='Contacted recruiter'),
                record(heuristic_id='H2', heuristic_name='Hiring evidence', value='Current job posting')])
        self.fake.get_doc = lambda *args: self.search
        perms = types.ModuleType('job_search.permissions')
        perms.require_doc = lambda *args: None
        perms.require_operator = lambda: None
        with patch.dict(sys.modules, {'frappe': self.fake, 'frappe.utils': self.fake.utils,
                                       'job_search.permissions': perms}):
            self.searches = load('searches.py', 'review_test_searches')
            with patch.dict(sys.modules, {'job_search.searches': self.searches}):
                self.workflow = load('workflow.py', 'review_test_workflow')

    def errors(self):
        return self.workflow._review_readiness_failures(self.job)

    def test_valid_complete_search_and_heuristics_pass(self):
        self.assertEqual([], self.errors())
        self.assertEqual([], self.searches.match_failures(self.job, self.search))

    def test_job_title_is_builtin_heuristic_not_exact_match(self):
        from job_search.heuristics import research_heuristics
        rows = research_heuristics(self.search)
        self.assertEqual('builtin:job-title', rows[0]['name'])
        self.assertEqual('Job Title', rows[0]['heuristic_name'])
        self.assertIn('job description should describe a role matching', rows[0]['description'])
        self.assertIn('- Python Engineer', rows[0]['description'])
        self.job.job_title = 'Backend Platform Architect'
        self.assertEqual([], self.searches.match_failures(self.job, self.search))
        self.assertEqual([], self.errors())
        self.job.research_heuristics[0].value = ' '
        self.assertIn("Research heuristic 'Job Title' requires a value", self.errors())
        self.job.research_heuristics.pop(0)
        self.assertIn("Research heuristic 'Job Title' is missing", self.errors())
        self.search.title_matches = ''
        self.assertEqual([], self.errors())

    def test_missing_and_disabled_search_are_rejected(self):
        self.job.active_job_search = ''
        self.assertIn('Active Job Search is required', self.errors())
        self.job.active_job_search = 'SEARCH1'
        self.search.enabled = 0
        self.assertIn('disabled', ' '.join(self.errors()))
        self.fake.db.exists = lambda *args: False
        self.assertIn('does not exist', ' '.join(self.errors()))

    def test_reports_every_failing_search_parameter(self):
        self.job.job_title = 'Designer'
        self.job.location = 'Salem, OR'
        self.job.employment_type = 'Contract'
        self.job.work_arrangement = 'Hybrid'
        self.job.seniority = 'Junior'
        self.job.posted_on = None
        self.job.compensation_min = 80000
        self.job.currency = 'EUR'
        self.job.compensation_period = 'Hour'
        errors = self.errors()
        for key in ('Location', 'Employment Type', 'Work Arrangement',
                    'Seniority', 'Posted On', 'Minimum Compensation', 'Currency',
                    'Compensation Period'):
            with self.subTest(key=key):
                self.assertIn(key, ' '.join(errors))
        self.assertEqual(8, len(errors))
        self.assertFalse(self.searches.matches(self.job, self.search))

    def test_missing_blank_duplicate_and_stale_heuristic_values(self):
        self.job.research_heuristics.pop()
        self.assertIn("Research heuristic 'Hiring evidence' is missing", self.errors())
        self.job.research_heuristics.append(record(heuristic_id='H2', heuristic_name='Hiring evidence', value='   '))
        self.assertIn("Research heuristic 'Hiring evidence' requires a value", self.errors())
        self.job.research_heuristics.append(record(heuristic_id='H2', heuristic_name='Hiring evidence', value='Evidence'))
        self.assertIn('Duplicate research heuristic', ' '.join(self.errors()))
        self.job.research_heuristics.append(record(heuristic_id='Other', heuristic_name='Old criterion', value='Old value'))
        self.assertIn('Unexpected research heuristic', ' '.join(self.errors()))

    def test_excluded_rejected_or_explicit_approval_required(self):
        self.job.globally_rejected = 1
        self.search.overrides = [record(job='JOB1', override='Exclude')]
        self.search.require_heuristics = 1
        errors = self.errors()
        self.assertIn('Job is globally rejected', errors)
        self.assertIn('Job is explicitly excluded from the active job search', errors)
        self.assertIn('Active job search requires an explicit Include override', errors)
        self.job.globally_rejected = 0
        self.search.overrides = [record(job='JOB1', override='Include')]
        self.assertEqual([], self.errors())

    def test_transition_gate_cannot_be_skipped_by_exception_flag(self):
        self.job.research_heuristics[1].value = '   '
        with self.assertRaisesRegex(ValueError, 'Personal contact'):
            self.workflow._validate_transition(self.job, 'Researching', 'Ready to Review')
        self.fake.flags.job_search_transition_context = record(
            get=lambda key, default=None: {'deal':'JOB1','exception':'special',
                'reason':'test','override_decision':'approval'}.get(key, default))
        self.workflow.require_decision = lambda *args: 'DECISION1'
        with self.assertRaisesRegex(ValueError, 'Personal contact'):
            self.workflow._validate_transition(self.job, 'Researching', 'Ready to Review')
        self.job.research_heuristics[1].value = 'Contacted recruiter'
        self.assertIsNotNone(self.workflow._validate_transition(self.job, 'Researching', 'Ready to Review'))

    def test_heuristics_reordered_by_search_keep_stable_identity(self):
        self.search.heuristics.reverse()
        self.assertEqual([], self.errors())
        self.search.heuristics.append(record(name='H3', heuristic_name='Additional review'))
        self.assertIn("Research heuristic 'Additional review' is missing", self.errors())


if __name__ == '__main__':
    unittest.main()
