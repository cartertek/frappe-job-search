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
        self.retrieved_on = self.retrieved_on or now_datetime()
