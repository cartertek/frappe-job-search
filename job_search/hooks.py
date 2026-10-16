app_name = "job_search"
app_title = "Frappe Job Search"
app_publisher = "Cartertek LLC"
app_description = "Research-first job search workflow for Frappe CRM"
app_email = "admin@cartertek.ai"
app_license = "MIT"
required_apps = ["frappe/crm"]
source_link = "https://github.com/cartertek/frappe-job-search"

after_install = "job_search.setup.after_install"
after_migrate = "job_search.setup.after_migrate"

fixtures = [
    {"dt": "Role", "filters": [["name", "in", ["Job Search Operator", "Job Search Approver"]]]},
    {"dt": "Custom Field", "filters": [["name", "in", [
        "CRM Deal-" + name for name in (
            "js_tab js_is_job_search js_job_title js_posting_url js_requisition_id "
            "js_employment_type js_work_arrangement js_location js_compensation_min "
            "js_compensation_max js_currency js_compensation_period js_seniority "
            "js_discovered_on js_posted_on js_deadline js_qualification "
            "js_qualification_rationale js_applied_on js_next_action_on js_priority "
            "js_stage js_closure_reason js_offer_details"
        ).split()
    ] + [
        "CRM Organization-" + name for name in (
            "js_tab js_careers_url js_employer_category js_employer_priority "
            "js_research_status js_last_researched js_employment_notes"
        ).split()
    ]]]},
]

doc_events = {
    "CRM Deal": {
        "validate": "job_search.workflow.validate_deal",
        "on_update": "job_search.workflow.record_transition",
        "after_insert": "job_search.workflow.record_transition",
    }
}
