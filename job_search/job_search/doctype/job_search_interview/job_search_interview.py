import frappe
from frappe.model.document import Document

from job_search.permissions import require_opportunity


class JobSearchInterview(Document):
    def validate(self):
        deal = require_opportunity(self.opportunity, "read")
        if self.application:
            parent = frappe.db.get_value("Job Search Application", self.application, "opportunity")
            if parent != deal.name:
                frappe.throw("Interview application does not belong to opportunity")
        if self.round is not None and self.round < 0:
            frappe.throw("Interview round must be nonnegative")

    def on_trash(self):
        frappe.throw("Interview history cannot be deleted")
