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


# Native Frappe non-editable child-grid row template. Unlike static grid columns,
# templates render full rich text and remain stable after opening/closing a row.
form_grid_templates = {
    "heuristics": "templates/includes/search_heuristic_row.html",
}
