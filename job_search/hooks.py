app_name = "job_search"
app_title = "Frappe Job Search"
app_publisher = "Cartertek LLC"
app_description = "Research-first job search workflow for Frappe CRM"
app_email = "admin@cartertek.ai"
app_license = "MIT"
required_apps = ["crm"]
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
            "js_stage js_closure_reason js_offer_details js_posting_digest "
            "js_research_digest js_agent_recommendation js_application_review "
            "js_interview_brief js_human_feedback js_human_action js_human_action_rationale "
            "js_review_request js_review_status js_review_assigned_to js_review_task "
            "js_posting_text js_latest_posting js_last_decision js_last_decision_record "
            "js_latest_application js_interview_schedule"
        ).split()
    ] + [
        "CRM Organization-" + name for name in (
            "js_tab js_careers_url js_employer_category js_employer_priority "
            "js_research_status js_last_researched js_employment_notes"
        ).split()
    ] + ["CRM Task-js_transition"]]]},
]

doc_events = {
    "CRM Deal": {
        "validate": "job_search.workflow.validate_deal",
        "before_save": "job_search.human.validate_human_action",
        "on_update": ["job_search.workflow.record_transition", "job_search.human.save_human_action"],
    }
}
