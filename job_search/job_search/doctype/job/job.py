from frappe.model.document import Document


class Job(Document):
    def validate(self):
        from job_search.workflow import validate_job
        validate_job(self)


form_grid_templates = {
    "research_heuristics": "templates/includes/job_heuristic_value_row.html",
}
