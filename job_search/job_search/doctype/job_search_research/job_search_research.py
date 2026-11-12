import frappe
from frappe.model.document import Document

from job_search.permissions import require_opportunity


class JobSearchResearch(Document):
    def validate(self):
        if not self.organization and not self.opportunity and not self.job:
            frappe.throw("Research must be linked to a Job, Opportunity, or Organization")
        if self.opportunity:
            deal = require_opportunity(self.opportunity, "read")
            if self.organization and self.organization != deal.organization:
                frappe.throw("Research employer differs from Deal employer")
            self.organization = deal.organization
        if self.job:
            job=frappe.get_doc('Job',self.job)
            if self.organization and self.organization!=job.organization:
                frappe.throw('Research Job belongs to another Organization')
            if self.opportunity and self.opportunity not in frappe.get_all(
                    'Opportunity Job',filters={'job':self.job},pluck='parent'):
                frappe.throw('Research Job is not associated with this Opportunity')
            self.organization=job.organization
        if self.status == "Verified" and (
            self.evidence_class not in ("Verified Fact", "Supported Interpretation") or not self.sources
        ):
            frappe.throw("Verified research needs cited facts or supported interpretations")
        if self.evidence_class == "Verified Fact" and not self.sources:
            frappe.throw("Verified facts must cite at least one source")
        if len({row.source for row in self.sources}) != len(self.sources):
            frappe.throw("Duplicate research source")
        if self.is_new():
            self.operator = frappe.session.user
