import frappe
from frappe.model.document import Document

from job_search.permissions import require_opportunity
from job_search.workflow import require_decision


class JobSearchApplication(Document):
    def validate(self):
        require_opportunity(self.opportunity, "read")
        require_decision(self.opportunity, "Authorize Application", self.authorization)
        if not self.submitted_on or not self.submission_method:
            frappe.throw("Submission date and method required")
        if not (self.resume or self.cover_letter or self.materials):
            frappe.throw("Submitted materials must be identified")
        if not (self.confirmation or self.reference_number):
            frappe.throw("Submission confirmation or reference required")
        existing = None
        if self.reference_number:
            existing = frappe.db.get_value("Job Search Application", {
                "opportunity": self.opportunity, "reference_number": self.reference_number,
            }, "name")
        if existing and existing != self.name:
            frappe.throw("Duplicate submission reference for opportunity")

    def after_insert(self):
        """Maintain the latest submission date on the opportunity without bypassing hooks."""
        from frappe.utils import getdate

        deal = require_opportunity(self.opportunity, "write")
        new_date = getdate(self.submitted_on)
        if not deal.applied_on or getdate(deal.applied_on) < new_date:
            deal.applied_on = new_date
            deal.save()

    def on_trash(self):
        frappe.throw("Submitted application history cannot be deleted")
