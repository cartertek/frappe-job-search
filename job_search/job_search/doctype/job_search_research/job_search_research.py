import frappe
from frappe.model.document import Document

from job_search.permissions import require_opportunity


class JobSearchResearch(Document):
    def validate(self):
        if not self.organization and not self.opportunity:
            frappe.throw("Research must be linked to an employer or opportunity")
        if self.opportunity:
            deal = require_opportunity(self.opportunity, "read")
            if self.organization and self.organization != deal.organization:
                frappe.throw("Research employer differs from Deal employer")
            self.organization = deal.organization
        if self.evidence_class == "Verified Fact" and not self.sources:
            frappe.throw("Verified facts must cite at least one source")
        if len({row.source for row in self.sources}) != len(self.sources):
            frappe.throw("Duplicate research source")
        if not self.operator:
            self.operator = frappe.session.user
