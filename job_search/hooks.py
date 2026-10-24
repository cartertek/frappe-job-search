app_name = "job_search"
app_title = "Frappe Job Search"
app_publisher = "Cartertek LLC"
app_description = "Standalone research-first job search workflow"
app_email = "admin@cartertek.ai"
app_license = "MIT"
source_link = "https://github.com/cartertek/frappe-job-search"

app_logo_url = "/assets/job_search/images/job-search.svg"
app_home = "/desk/job-search"

add_to_apps_screen = [
    {
        "name": "job_search",
        "logo": app_logo_url,
        "title": "Job Search",
        "route": app_home,
        "has_permission": "job_search.permissions.can_access_app",
        "sequence_id": 20,
    }
]

after_install = "job_search.setup.after_install"
after_migrate = "job_search.setup.after_migrate"
fixtures = [{"dt": "Role", "filters": [["name", "in", ["Job Search Operator", "Job Search Approver"]]]}]

doc_events = {
    "Job Search Opportunity": {
        "validate": "job_search.workflow.validate_deal",
        "before_save": "job_search.human.validate_human_action",
        "on_update": ["job_search.workflow.record_transition", "job_search.human.save_human_action"],
    }
}
