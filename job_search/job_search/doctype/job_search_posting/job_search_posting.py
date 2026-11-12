import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, nowdate

from job_search.permissions import require_job, require_opportunity
from job_search.postings import content_hash


class JobSearchPosting(Document):
    def validate(self):
        role = require_job(self.job, "read")
        if self.organization and self.organization != role.organization:
            frappe.throw("Posting Organization differs from Job Organization")
        self.organization = role.organization
        if self.opportunity:
            deal = require_opportunity(self.opportunity, "read")
            if deal.organization != role.organization:
                frappe.throw("Posting Opportunity belongs to another Organization")
            if self.opportunity not in frappe.get_all(
                    'Opportunity Job',filters={'job':role.name},pluck='parent'):
                frappe.throw("Posting Job is not associated with this Opportunity")
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
            for field in ("job", "opportunity", "organization", "source_url", "source_name",
                          "posting_title", "description", "retrieved_on", "content_hash",
                          "supersedes", "snapshot"):
                if self.get(field) != old.get(field):
                    frappe.throw(f"Posting snapshot field {field} is immutable; capture a new revision")
        else:
            self.content_hash = digest

    def on_trash(self):
        frappe.throw("Posting snapshots must be retained")
