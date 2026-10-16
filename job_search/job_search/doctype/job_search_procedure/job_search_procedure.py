import frappe
from frappe.model.document import Document


class JobSearchProcedure(Document):
    def validate(self):
        duplicate = frappe.db.get_value("Job Search Procedure", {
            "procedure_id": self.procedure_id, "version": self.version,
        }, "name")
        if duplicate and duplicate != self.name:
            frappe.throw("Procedure identifier and version must be unique")
        identifiers = [step.step_id for step in self.steps]
        if not identifiers or len(identifiers) != len(set(identifiers)):
            frappe.throw("Procedure requires unique, nonempty step identifiers")
        previous = self.get_doc_before_save()
        if previous and previous.status in ("Active", "Retired"):
            frappe.throw("Published procedure versions are immutable; publish a new version instead")

    def on_trash(self):
        if self.status in ("Active", "Retired"):
            frappe.throw("Published procedure versions must be retained")
