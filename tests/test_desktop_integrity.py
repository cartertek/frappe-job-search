"""Regression checks for disappearing Frappe desktop icons."""
import unittest

from job_search.desktop_integrity import find_desktop_layout_issues


class DesktopLayoutIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.icons = [
            {'name': 'Framework', 'label': 'Framework', 'parent_icon': None,
             'standard': 1, 'owner': 'Administrator', 'icon_type': 'App'},
            {'name': 'Job Search', 'label': 'Job Search', 'parent_icon': None,
             'standard': 0, 'owner': 'Administrator', 'icon_type': 'Link', 'link_to': 'Job Search'},
            {'name': 'Wiki', 'label': 'Wiki', 'parent_icon': None,
             'standard': 0, 'owner': 'Administrator', 'icon_type': 'App'},
            {'name': 'Wiki App', 'label': 'Wiki App', 'parent_icon': 'Wiki',
             'standard': 0, 'owner': 'assistant@example.com', 'icon_type': 'Link', 'link_to': 'Wiki'},
        ]
        self.layout = {'person@example.com': [
            {'name': 'Framework', 'label': 'Framework'},
            {'name': 'Job Search', 'label': 'Job Search'},
            {'name': 'Wiki', 'label': 'Wiki'},
            {'name': 'Wiki App', 'label': 'Wiki App', 'parent_icon': 'Wiki'},
        ]}

    def test_healthy_shared_wiki_link(self):
        self.assertEqual([], find_desktop_layout_issues(self.icons, self.layout))

    def test_missing_database_parent(self):
        self.icons[1]['parent_icon'] = 'Frappe Job Search'
        kinds = {i['kind'] for i in find_desktop_layout_issues(self.icons, self.layout)}
        self.assertIn('missing_database_parent', kinds)
        self.assertIn('unavailable_database_parent', kinds)

    def test_missing_saved_icon(self):
        self.icons.pop()
        self.assertIn('missing_saved_icon',
                      {i['kind'] for i in find_desktop_layout_issues(self.icons, self.layout)})

    def test_private_assistant_created_app_icon_is_not_shared(self):
        self.icons[-1]['icon_type'] = 'App'
        self.assertIn('unshared_saved_icon',
                      {i['kind'] for i in find_desktop_layout_issues(self.icons, self.layout)})

    def test_saved_layout_parent_not_present(self):
        self.layout['person@example.com'].pop(2)
        self.assertIn('missing_saved_parent',
                      {i['kind'] for i in find_desktop_layout_issues(self.icons, self.layout)})

    def test_missing_icon_with_different_name_but_matching_label(self):
        self.layout['person@example.com'][-1]['name'] = 'My Wiki'
        self.assertEqual([], find_desktop_layout_issues(self.icons, self.layout))

    def test_private_workspace_link_not_shared(self):
        self.assertIn('unshared_saved_icon',
                      {i['kind'] for i in find_desktop_layout_issues(
                          self.icons, self.layout, private_workspaces=['Wiki'])})


if __name__ == '__main__':
    unittest.main()
