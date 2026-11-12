"""Safety checks for the official Research Handbook migration."""
import hashlib
import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('wiki_issue15',ROOT/'scripts/update_wiki_issue15.py')
wiki=importlib.util.module_from_spec(spec)
spec.loader.exec_module(wiki)


class WikiIssue15Tests(unittest.TestCase):
    def test_refuses_unrecognized_sections_and_routes(self):
        with self.assertRaisesRegex(ValueError,'start-here missing anchor'):
            wiki.change('start-here','# Job Search Research Handbook')
        with self.assertRaisesRegex(ValueError,'non-handbook'):
            wiki.convert([{'route':'private/page','content':'example'}])

    def test_section_change_preserves_unrelated_sections(self):
        text='# Wiki\n\n## A\n\nOld A\n\n## B\n\nOriginal B\n'
        self.assertEqual(wiki.section(text,'A','New A'),
                         '# Wiki\n\n## A\n\nNew A\n\n## B\n\nOriginal B\n')

    def test_wiki_patch_tracks_original_hash(self):
        old=(
            '# Contact Research\n\n'
            '## Evidence grades (working framework, not measured probabilities)\n\n'
            'Example\n'
        )
        entries=wiki.convert([{'name':'test','route':'docs/research-handbook/contact-research',
                                'owner':'assistant','content':old}])
        self.assertEqual(entries[0]['original_sha256'],hashlib.sha256(old.encode()).hexdigest())
        self.assertIn('Relationship to the Opportunity',entries[0]['content'])
        self.assertNotEqual(entries[0]['content'],old)

if __name__=='__main__':
    unittest.main()
