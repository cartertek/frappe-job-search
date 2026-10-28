from frappe.model.document import Document


class JobSearchOpportunity(Document):
    pass


# Native child-table row template: full-width, properly aligned grid columns.
form_grid_templates = {
    "research_heuristics": "templates/includes/job_heuristic_value_row.html",
}
