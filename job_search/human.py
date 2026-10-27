"""Human-only decisions entered on Job Search Opportunity's native Data tab.

The request fields are one-time inputs, not an authorization record. Only an
approver's signed-in request may produce the immutable Job Search Decision.
"""

import frappe

from job_search.permissions import require_approver

DECISION_OPTIONS = (
    "Pursue", "Decline", "Authorize Application", "Decline Application",
    "Accept Offer", "Reject Offer", "Withdraw", "Override",
)


REQUEST_DECISIONS = {
    "Pursue or Decline": {"Pursue", "Decline"},
    "Authorize or Decline Application": {"Authorize Application", "Decline Application"},
    "Accept or Reject Offer": {"Accept Offer", "Reject Offer"},
    "Withdraw": {"Withdraw"},
    "Override": {"Override"},
}


def validate_human_action(doc, method=None):
    action = (doc.get("human_action") or "").strip()
    rationale = (doc.get("human_action_rationale") or "").strip()
    if not action:
        if rationale:
            frappe.throw("Select a human decision when entering a decision rationale")
        return
    if doc.is_new():
        frappe.throw("Human decisions require an existing Job Search opportunity")
    require_approver()
    doc.check_permission("write")
    if action not in DECISION_OPTIONS:
        frappe.throw("Invalid human decision")
    if not rationale:
        frappe.throw("Human decision rationale required")
    if doc.get("review_status") == "Pending":
        if action not in REQUEST_DECISIONS.get(doc.get("review_request"), set()):
            frappe.throw("Decision does not match pending human review")
        assignee = doc.get("review_assigned_to")
        if assignee and assignee != frappe.session.user and "System Manager" not in frappe.get_roles():
            frappe.throw("Review assigned to another human approver", frappe.PermissionError)


def save_human_action(doc, method=None):
    action = (doc.get("human_action") or "").strip()
    if not action:
        return
    # Frappe ORM enforces the human approver role and captures the real actor.
    decision_doc = frappe.get_doc({
        "doctype": "Job Search Decision", "opportunity": doc.name,
        "decision": action, "rationale": doc.human_action_rationale,
    }).insert()
    doc.db_set("last_decision", f"{action} by {decision_doc.authorized_by} "
               f"at {decision_doc.authorized_at}: {doc.human_action_rationale}"[:1000],
               update_modified=False)
    doc.db_set("last_decision_record", decision_doc.name, update_modified=False)
    # Clear the one-shot form inputs; the immutable Decision document persists.
    doc.db_set("human_action", "", update_modified=False)
    doc.db_set("human_action_rationale", "", update_modified=False)
    doc.human_action = ""
    doc.human_action_rationale = ""
    if doc.get("review_status") == "Pending":
        doc.db_set("review_status", "Completed", update_modified=False)
        if doc.get("review_task"):
            task = frappe.get_doc("Job Search Task", doc.review_task)
            # A signed human action can close its linked review task.
            task.check_permission("write")
            task.status = "Done"
            task.save()
        if doc.get("review_assignment"):
            todo = frappe.get_doc("ToDo", doc.review_assignment)
            if todo.reference_type == "Job Search Opportunity" and todo.reference_name == doc.name:
                todo.status = "Closed"
                todo.save(ignore_permissions=True)

    # An explicit human Decline closes the opportunity; do not leave it in
    # Researching waiting for a second manual/agent transition.
    if action == "Decline" and doc.status not in ("Closed", "Rejected", "Withdrawn"):
        doc.closure_reason = f"Human declined opportunity (decision {decision_doc.name})"
        doc.status = "Closed"
        doc.save()
