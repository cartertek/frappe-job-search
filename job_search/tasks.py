"""Stage-entry tasks are created with the Deal change, never external messages."""

import frappe

STAGE_ACTIONS = {
    "Discovered": "Research new opportunity",
    "Researching": "Complete employer and role research",
    "Qualified": "Prepare application requirements",
    "Preparing": "Assemble and review application materials",
    "Applied": "Plan application follow-up",
    "Screening": "Prepare for employer screening",
    "Interviewing": "Prepare for interview and record outcome",
    "Offer": "Review offer and make a decision",
}


def create_stage_task(deal, transition):
    action = STAGE_ACTIONS.get(deal.js_stage)
    if not action:
        return None
    # A stable record link prevents retries from creating a second task.
    existing = frappe.db.get_value("Job Search Task", {"js_transition": transition.name}, "name")
    if existing:
        return existing
    due = deal.js_next_action_on or deal.js_deadline
    doc = frappe.get_doc({
        "doctype": "Job Search Task", "title": f"{action}: {deal.js_job_title}",
        "status": "Todo", "priority": "High" if deal.js_stage == "Offer" else "Medium",
        "due_date": due, "assigned_to": deal.deal_owner or frappe.session.user,
        "opportunity": deal.name,
        "js_transition": transition.name,
        "description": f"Generated on entry to Job Search stage {deal.js_stage}. "
                       f"Source transition: {transition.name}. Complete or cancel as appropriate.",
    })
    doc.insert()  # Enforce Job Search Task permissions and retain the real initiating user.
    return doc.name
