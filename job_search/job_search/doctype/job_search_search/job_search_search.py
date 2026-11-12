import frappe
from frappe.model.document import Document

from job_search.display import opportunity_label
from job_search.recency import active_window_start


class JobSearchSearch(Document):
    def validate(self):
        observed = set()
        for row in self.overrides:
            if row.opportunity in observed:
                frappe.throw(f"Duplicate override for opportunity {opportunity_label(row.opportunity)}")
            observed.add(row.opportunity)
            if row.override not in ("Include", "Exclude"):
                frappe.throw("Invalid opportunity override")
        strategies = set()
        for row in self.research_strategies:
            if row.research_strategy in strategies:
                frappe.throw(f'Duplicate research strategy: {row.research_strategy}')
            strategies.add(row.research_strategy)
            if row.priority_override is not None and int(row.priority_override) < 0:
                frappe.throw('Research strategy priority override cannot be negative')
        if self.salary_min is not None and self.salary_min < 0:
            frappe.throw("Minimum compensation cannot be negative")
        try:
            active_window_start(self.active_in_past_count, self.active_in_past_unit)
        except ValueError as exc:
            frappe.throw(str(exc))


# Native Frappe non-editable child-grid row template. Unlike static grid columns,
# templates render full rich text and remain stable after opening/closing a row.
form_grid_templates = {
    "heuristics": "templates/includes/search_heuristic_row.html",
}
