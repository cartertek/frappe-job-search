"""Issue #14: priority-aware reusable research strategies."""
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'job_search/job_search/doctype'


def record(**kwargs):
    return types.SimpleNamespace(**kwargs)


class ResearchStrategyTests(unittest.TestCase):
    def setUp(self):
        self.records = {
            'A': record(name='A', strategy_name='A strategy', description='Follow A', default_priority=30),
            'B': record(name='B', strategy_name='B strategy', description='Follow B', default_priority=5),
            'C': record(name='C', strategy_name='C strategy', description='Follow C', default_priority=20),
        }
        fake = types.ModuleType('frappe')
        fake.throw = lambda msg: (_ for _ in ()).throw(ValueError(msg))
        model = types.ModuleType('frappe.model')
        document = types.ModuleType('frappe.model.document')
        document.Document = object
        perms = types.ModuleType('job_search.permissions')
        perms.require_doc = lambda dt, name, permission='read': self.records[name]
        perms.require_operator = lambda: None
        self.search = record(research_strategies=[
            record(research_strategy='A', priority_override=0, idx=1),
            record(research_strategy='B', priority_override=50, idx=2),
            record(research_strategy='C', priority_override=1, idx=3),
        ], overrides=[], salary_min=None,
            active_in_past_count=None, active_in_past_unit=None)
        with patch.dict(sys.modules, {'frappe':fake, 'frappe.model':model,
                    'frappe.model.document':document, 'job_search.permissions':perms}):
            path=ROOT/'job_search/strategies.py'
            spec=importlib.util.spec_from_file_location('test_issue14_strategies',path)
            self.strategy=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(self.strategy)
            path=BASE/'job_search_search/job_search_search.py'
            spec=importlib.util.spec_from_file_location('test_issue14_search',path)
            module=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.search_validator=module.JobSearchSearch.validate
            path=BASE/'research_strategy/research_strategy.py'
            spec=importlib.util.spec_from_file_location('test_issue14_strategy_doc',path)
            module=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self.strategy_validator=module.ResearchStrategy.validate

    def test_priority_override_and_inheritance(self):
        result=self.strategy.ordered_strategies(self.search)
        self.assertEqual([r['strategy'] for r in result],['C','A','B'])
        self.assertEqual([r['effective_priority'] for r in result],[1,30,50])
        self.assertEqual(result[1]['priority_override'],0)
        self.assertEqual(result[1]['instructions'],'Follow A')
        self.search.research_strategies[1].priority_override=None
        self.assertEqual([r['strategy'] for r in self.strategy.ordered_strategies(self.search)],['C','B','A'])

    def test_priority_ties_are_stable(self):
        self.search.research_strategies[0].priority_override=1
        self.assertEqual([r['strategy'] for r in self.strategy.ordered_strategies(self.search)],['A','C','B'])

    def test_duplicate_assignments_are_rejected(self):
        self.search.research_strategies[1].research_strategy='A'
        with self.assertRaisesRegex(ValueError,'Duplicate research strategy'):
            self.search_validator(self.search)

    def test_negative_override_is_rejected(self):
        self.search.research_strategies[1].priority_override=-3
        with self.assertRaisesRegex(ValueError,'cannot be negative'):
            self.search_validator(self.search)

    def test_research_strategy_requires_valid_default_and_instructions(self):
        doc=record(strategy_name='Lead discovery',description='Do this',default_priority=1)
        self.strategy_validator(doc)
        doc.default_priority=0
        with self.assertRaisesRegex(ValueError,'positive integer'):
            self.strategy_validator(doc)
        doc.default_priority=1
        doc.description=' '
        with self.assertRaisesRegex(ValueError,'Research Instructions'):
            self.strategy_validator(doc)

    def test_search_table_references_top_level_strategy(self):
        search=json.loads((BASE/'job_search_search/job_search_search.json').read_text())
        table=next(f for f in search['fields'] if f['fieldname']=='research_strategies')
        self.assertEqual(table['options'],'Assigned Research Strategy')
        child=json.loads((BASE/'assigned_research_strategy/assigned_research_strategy.json').read_text())
        self.assertEqual(child['fields'][0]['options'],'Research Strategy')


if __name__=='__main__':
    unittest.main()
