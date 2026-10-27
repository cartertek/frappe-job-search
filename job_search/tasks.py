"""Stage-entry tasks are created with the Deal change, never external messages."""

import frappe

STAGE_ACTIONS = {
    "Discovered": "Research new opportunity",
    "Researching": "Complete employer and role research",
    "Ready to Review": "Review research and decide qualification",
    "Qualified": "Prepare application requirements",
    "Applied": "Plan application follow-up",
    "Interviewing": "Prepare for interview and record outcome",
}


def create_stage_task(deal, transition):
    action = STAGE_ACTIONS.get(deal.status)
    if not action:
        return None
    # A stable record link prevents retries from creating a second task.
    existing = frappe.db.get_value("Job Search Task", {"transition": transition.name}, "name")
    if existing:
        return existing
    due = deal.next_action_on or deal.deadline
    doc = frappe.get_doc({
        "doctype": "Job Search Task", "title": f"{action}: {deal.job_title}",
        "status": "Todo", "priority": "High" if deal.status == "Ready to Review" else "Medium",
        "due_date": due, "assigned_to": frappe.session.user,
        "opportunity": deal.name,
        "transition": transition.name,
        "description": f"Generated on entry to Job Search stage {deal.status}. "
                       f"Source transition: {transition.name}. Complete or cancel as appropriate.",
    })
    doc.insert()  # Enforce Job Search Task permissions and retain the real initiating user.
    return doc.name
