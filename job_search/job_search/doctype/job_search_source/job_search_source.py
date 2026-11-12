import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from job_search.permissions import require_opportunity


class JobSearchSource(Document):
    def validate(self):
        if not self.url and not self.archive:
            frappe.throw("Source requires a URL or archived attachment")
        if self.opportunity:
            deal = require_opportunity(self.opportunity, "read")
            if self.organization and self.organization != deal.organization:
                frappe.throw("Source organization differs from Deal organization")
            self.organization = deal.organization
        if self.job:
            job=frappe.get_doc('Job',self.job)
            if self.organization and self.organization!=job.organization:
                frappe.throw('Source organization differs from Job Organization')
            if self.opportunity and self.opportunity not in frappe.get_all(
                    'Opportunity Job',filters={'job':self.job},pluck='parent'):
                frappe.throw('Source Opportunity is not associated with its Job')
            self.organization=job.organization
        self.retrieved_on = self.retrieved_on or now_datetime()
