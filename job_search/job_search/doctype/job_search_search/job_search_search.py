import frappe
from frappe.model.document import Document


class JobSearchSearch(Document):
    def validate(self):
        observed = set()
        for row in self.overrides:
            if row.job in observed:
                frappe.throw(f"Duplicate override for job {row.job}")
            observed.add(row.job)
            if row.override not in ("Include", "Exclude"):
                frappe.throw("Invalid job override")
        if self.salary_min is not None and self.salary_min < 0:
            frappe.throw("Minimum compensation cannot be negative")
