import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, nowdate

from job_search.permissions import require_opportunity
from job_search.postings import content_hash


class JobSearchPosting(Document):
    def validate(self):
        deal = require_opportunity(self.opportunity, "read")
        if self.organization and self.organization != deal.organization:
            frappe.throw("Posting employer differs from Deal employer")
        self.organization = deal.organization
        if not (self.description or "").strip():
            frappe.throw("A posting must preserve the complete captured description")
        if not self.retrieved_on:
            self.retrieved_on = now_datetime()
        if not self.first_observed:
            self.first_observed = nowdate()
        self.last_observed = self.last_observed or self.first_observed
        digest = content_hash(self.description)
        old = self.get_doc_before_save() if not self.is_new() else None
        if old:
            for field in ("opportunity", "organization", "source_url", "source_name",
                          "posting_title", "description", "retrieved_on", "content_hash",
                          "supersedes", "snapshot"):
                if self.get(field) != old.get(field):
                    frappe.throw(f"Posting snapshot field {field} is immutable; capture a new revision")
        else:
            self.content_hash = digest

    def on_trash(self):
        frappe.throw("Posting snapshots must be retained")
