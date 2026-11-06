import frappe
from frappe.model.document import Document


class JobSearchResearchStrategy(Document):
    def validate(self):
        if not (self.strategy_name or '').strip():
            frappe.throw('Research Strategy Name is required')
        if not (self.description or '').strip():
            frappe.throw('Research Instructions are required')
        if not self.default_priority or int(self.default_priority) < 1:
            frappe.throw('Default Priority must be a positive integer (1 is highest)')
