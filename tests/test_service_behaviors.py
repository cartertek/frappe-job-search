"""Focused behavior tests without requiring an installed bench or database.

Real-site integration tests remain mandatory; these protect deterministic state logic
and the outward contract of the critical service methods in isolation.
"""

import importlib.util
import sys
import types
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[1] / "job_search"


def load_app_module(relative_path, name, frappe, **dependencies):
    helpers = types.ModuleType("frappe.utils")
    helpers.now_datetime = lambda: "2026-10-16 12:00:00"
    helpers.nowdate = lambda: "2026-10-16"
    helpers.getdate = lambda value: date.fromisoformat(str(value)[:10])
    modules = {"frappe": frappe, "frappe.utils": helpers, **dependencies}
    with patch.dict(sys.modules, modules):
        spec = importlib.util.spec_from_file_location(name, PACKAGE / relative_path)
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
    return loaded


class FakeDocument:
    def __init__(self, fields, records):
        self.__dict__.update(fields)
        self._records = records

    def insert(self):
        self.name = f"REC-{len(self._records) + 1}"
        self._records.append(self)
        return self


class PostingBehavior(unittest.TestCase):
    def make_service(self):
        self.postings = []
        fake = types.ModuleType("frappe")
        fake.throw = lambda message: (_ for _ in ()).throw(ValueError(message))
        def get_value(doctype, filters, field, **kwargs):
            for post in reversed(self.postings):
                if post.opportunity != filters.get("opportunity"):
                    continue
                if post.source_name != filters.get("source_name"):
                    continue
                url = filters.get("source_url")
                if isinstance(url, list) and url == ["is", "not set"]:
                    if post.source_url:
                        continue
                elif post.source_url != url:
                    continue
                if isinstance(field, list):
                    return types.SimpleNamespace(name=post.name, content_hash=post.content_hash)
                return post.name
            return None
        fake.db = types.SimpleNamespace(get_value=get_value)
        def get_doc(data):
            data["content_hash"] = service.content_hash(data["description"])
            return FakeDocument(data, self.postings)
        fake.get_doc = get_doc
        fake_perms = types.ModuleType("job_search.permissions")
        fake_perms.require_operator = lambda: None
        fake_perms.require_opportunity = lambda name, ptype="read": types.SimpleNamespace(
            name=name, organization="Example Ltd", js_job_title="Developer", js_requisition_id="42"
        )
        service = load_app_module("postings.py", "test_postings_module", fake,
                                  **{"job_search.permissions": fake_perms})
        return service

    def test_unchanged_import_is_idempotent_but_new_text_is_preserved(self):
        service = self.make_service()
        params = {"opportunity": "D-1", "source_name": "Employer",
                  "source_url": "https://example.org/job/42"}
        a = service.capture_posting(description="Original description", **params)
        b = service.capture_posting(description="Original description", **params)
        c = service.capture_posting(description="Changed description", **params)
        self.assertTrue(a["created"])
        self.assertFalse(b["created"])
        self.assertEqual(a["posting"], b["posting"])
        self.assertTrue(c["created"])
        self.assertEqual(a["posting"], c["supersedes"])
        d = service.capture_posting(description="Original description", **params)
        self.assertTrue(d["created"])
        self.assertEqual(c["posting"], d["supersedes"])
        self.assertEqual(["Original description", "Changed description", "Original description"],
                         [p.description for p in self.postings])

    def test_empty_captured_description_is_not_saved(self):
        service = self.make_service()
        with self.assertRaisesRegex(ValueError, "description is required"):
            service.capture_posting("D-1", description=" ", source_name="Employer")
        self.assertFalse(self.postings)


class TaskBehavior(unittest.TestCase):
    def test_stage_task_has_provenance_and_is_idempotent(self):
        rows = []
        fake = types.ModuleType("frappe")
        fake.session = types.SimpleNamespace(user="operator@example.org")
        fake.db = types.SimpleNamespace(get_value=lambda dt, filters, field: next(
            (r.name for r in rows if r.js_transition == filters["js_transition"]), None
        ))
        fake.get_doc = lambda data: FakeDocument(data, rows)
        tasks = load_app_module("tasks.py", "test_tasks_module", fake)
        deal = types.SimpleNamespace(js_stage="Applied", js_job_title="Engineer", name="D-1",
             deal_owner=None, js_next_action_on="2026-10-22", js_deadline="2026-11-01")
        transition = types.SimpleNamespace(name="T-1")
        first = tasks.create_stage_task(deal, transition)
        second = tasks.create_stage_task(deal, transition)
        self.assertEqual(first, second)
        self.assertEqual(1, len(rows))
        self.assertEqual("CRM Deal", rows[0].reference_doctype)
        self.assertEqual("D-1", rows[0].reference_docname)
        self.assertEqual("2026-10-22", rows[0].due_date)
        self.assertEqual("operator@example.org", rows[0].assigned_to)
        deal.js_stage = "Closed"
        self.assertIsNone(tasks.create_stage_task(deal, types.SimpleNamespace(name="T-2")))
        self.assertEqual(1, len(rows))


class QueueBehavior(unittest.TestCase):
    def test_due_date_boundaries(self):
        fake = types.ModuleType("frappe")
        fake_perms = types.ModuleType("job_search.permissions")
        fake_perms.require_operator = lambda: None
        queues = load_app_module("queues.py", "test_queues_module", fake,
                                 **{"job_search.permissions": fake_perms})
        self.assertEqual("unscheduled", queues.classify_due(None, "2026-10-16"))
        self.assertEqual("overdue", queues.classify_due("2026-10-15", "2026-10-16"))
        self.assertEqual("upcoming", queues.classify_due("2026-10-16", "2026-10-16"))
        self.assertEqual("upcoming", queues.classify_due("2026-10-30", "2026-10-16"))
        self.assertEqual("later", queues.classify_due("2026-10-31", "2026-10-16"))


if __name__ == "__main__":
    unittest.main()
