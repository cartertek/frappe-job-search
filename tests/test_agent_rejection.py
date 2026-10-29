"""Agents can close unsuitable research without forging human approval."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class AgentRejection(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.job = types.SimpleNamespace(name='job1', status='Researching', organization='org1', active_job_search='search1',
            globally_rejected=0, save=lambda: self.calls.append('save'),
            add_comment=lambda kind, text: self.calls.append(('comment', kind, text)))
        frappe = types.ModuleType('frappe')
        frappe.throw = lambda msg: (_ for _ in ()).throw(ValueError(msg))
        frappe.get_doc = lambda x: (_ for _ in ()).throw(AssertionError('Human decision must not be created'))
        perms = types.ModuleType('job_search.permissions')
        perms.require_operator = lambda: self.calls.append('operator')
        perms.require_approver = lambda: self.calls.append('approver')
        perms.require_opportunity = lambda *args: self.job
        perms.require_doc = lambda *args: types.SimpleNamespace(overrides=[], save=lambda: None,
            append=lambda *a: None)
        workflow = types.ModuleType('job_search.workflow')
        workflow._has_research = lambda *a: True
        workflow._has_completed_research_procedure = lambda *a: True
        with patch.dict(sys.modules, {'frappe': frappe, 'job_search.permissions': perms,
                                      'job_search.workflow': workflow}):
            path = Path(__file__).resolve().parents[1] / 'job_search/workflow_actions.py'
            spec = importlib.util.spec_from_file_location('agent_rejection_test', path)
            self.module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.module)

    def test_agent_rejects_job_without_human_decision(self):
        result = self.module.perform_action('job1','reject',rationale='Fails remote requirement',scope='job')
        self.assertEqual('Rejected', result['status'])
        self.assertEqual(1, self.job.globally_rejected)
        self.assertIn('operator', self.calls)
        self.assertNotIn('approver', self.calls)
        self.assertTrue(any(c[0]=='comment' and 'Fails remote requirement' in c[2]
                            for c in self.calls if isinstance(c, tuple)))

    def test_search_only_rejects_status_without_global_rejection(self):
        result = self.module.perform_action('job1', 'reject', rationale='Outside scope',
                                            scope='search', search='search1')
        self.assertEqual('Rejected', result['status'])
        self.assertEqual(0, self.job.globally_rejected)
        self.assertIn('save', self.calls)
        self.assertTrue(any(c[0] == 'comment' and 'Outside scope' in c[2]
                            for c in self.calls if isinstance(c, tuple)))
        self.assertNotIn('approver', self.calls)

    def test_search_only_defaults_to_active_job_search(self):
        result = self.module.perform_action('job1', 'reject',
            rationale='Does not match criteria', scope='search')
        self.assertEqual('Rejected', result['status'])
        self.assertNotIn('approver', self.calls)

    def test_search_only_without_search_raises_clear_error(self):
        self.job.active_job_search = None
        with self.assertRaisesRegex(ValueError, 'Select a search'):
            self.module.perform_action('job1', 'reject',
                rationale='Not a match', scope='search')
        self.assertEqual('Researching', self.job.status)

    def test_search_only_keeps_accepted_status(self):
        self.job.status = 'Accepted'
        result = self.module.perform_action('job1', 'reject', rationale='Exclude from this search',
                                            scope='search', search='search1')
        self.assertEqual('Accepted', result['status'])
        self.assertEqual(0, self.job.globally_rejected)

    def test_organization_rejection_updates_initiating_job_status(self):
        result = self.module.perform_action('job1', 'reject',
            rationale='Organization not suitable', scope='organization')
        self.assertEqual('Rejected', result['status'])
        self.assertEqual(0, self.job.globally_rejected)
        self.assertIn('save', self.calls)
        self.assertNotIn('approver', self.calls)

    def test_organization_rejection_preserves_accepted_status(self):
        self.job.status = 'Accepted'
        result = self.module.perform_action('job1', 'reject',
            rationale='No longer relevant', scope='organization')
        self.assertEqual('Accepted', result['status'])

    def test_research_handoff_uses_operator(self):
        self.module.perform_action('job1', 'ready_to_review')
        self.assertIn('operator', self.calls)
        self.assertNotIn('approver', self.calls)

    def test_qualification_still_requires_approver(self):
        self.job.status = 'Ready to Review'
        self.module._decision = lambda *args: None
        self.module.perform_action('job1', 'qualify', rationale='Approved')
        self.assertIn('approver', self.calls)
        self.assertNotIn('operator', self.calls)

    def test_rejection_requires_reason(self):
        with self.assertRaisesRegex(ValueError,'rationale'):
            self.module.perform_action('job1','reject',scope='job')
        self.assertFalse(any(isinstance(c,tuple) for c in self.calls))
