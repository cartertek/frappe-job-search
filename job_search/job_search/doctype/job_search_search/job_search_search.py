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
        strategies = set()
        for row in self.research_strategies:
            if row.research_strategy in strategies:
                frappe.throw(f'Duplicate research strategy: {row.research_strategy}')
            strategies.add(row.research_strategy)
            if row.priority_override is not None and int(row.priority_override) < 0:
                frappe.throw('Research strategy priority override cannot be negative')
        if self.salary_min is not None and self.salary_min < 0:
            frappe.throw("Minimum compensation cannot be negative")


# Native Frappe non-editable child-grid row template. Unlike static grid columns,
# templates render full rich text and remain stable after opening/closing a row.
form_grid_templates = {
    "heuristics": "templates/includes/search_heuristic_row.html",
}
