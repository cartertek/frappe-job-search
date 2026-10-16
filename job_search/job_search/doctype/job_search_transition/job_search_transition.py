import frappe
from frappe.model.document import Document


class JobSearchTransition(Document):
    def validate(self):
        if not self.is_new():
            frappe.throw("Workflow history is immutable")

    def on_trash(self):
        frappe.throw("Workflow history cannot be deleted")
