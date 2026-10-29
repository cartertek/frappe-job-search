"""Verify a one-time, non-destructive field migration and API naming contract."""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / 'job_search'


class MigrationContract(unittest.TestCase):
    def test_renames_preserve_old_columns_and_only_fill_null_destinations(self):
        tree = ast.parse((ROOT / 'setup/__init__.py').read_text())
        migration = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                         and n.name == 'migrate_semantic_job_fields')
        source = ast.get_source_segment((ROOT / 'setup/__init__.py').read_text(), migration)
        for old, new in {
            'posting_digest': 'job_description',
            'research_digest': 'research_findings',
            'agent_recommendation': 'research_recommendation',
            'application_review': 'application_materials_for_review',
            'interview_brief': 'interview_preparation',
            'human_feedback': 'human_feedback_and_instructions',
        }.items():
            self.assertIn(f'"{old}": "{new}"', source)
        self.assertIn('IS NULL', source)
        self.assertIn('set_default(marker, "1")', source)
        self.assertNotIn('DROP', source.upper())
        self.assertIn('migrate_semantic_job_fields()', (ROOT / 'setup/__init__.py').read_text())

    def test_review_api_accepts_new_and_legacy_names(self):
        tree = ast.parse((ROOT / 'api.py').read_text())
        f = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == 'publish_human_review')
        names = {a.arg for a in f.args.args}
        for field in ('job_description', 'research_findings', 'research_recommendation',
                      'application_materials_for_review', 'interview_preparation',
                      'posting_digest', 'research_digest', 'recommendation',
                      'application_review', 'interview_brief'):
            self.assertIn(field, names)


if __name__ == '__main__':
    unittest.main()
