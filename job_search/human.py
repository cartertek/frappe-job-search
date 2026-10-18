"""Human-only decisions entered on CRM Deal's native Data tab.

The request fields are one-time inputs, not an authorization record. Only an
approver's signed-in request may produce the immutable Job Search Decision.
"""

import frappe

from job_search.permissions import require_approver

DECISION_OPTIONS = (
    "Pursue", "Decline", "Authorize Application", "Decline Application",
    "Accept Offer", "Reject Offer", "Withdraw", "Override",
)


def validate_human_action(doc, method=None):
    action = (doc.get("js_human_action") or "").strip()
    rationale = (doc.get("js_human_action_rationale") or "").strip()
    if not action:
        if rationale:
            frappe.throw("Select a human decision when entering a decision rationale")
        return
    if not doc.get("js_is_job_search") or doc.is_new():
        frappe.throw("Human decisions require an existing Job Search opportunity")
    require_approver()
    doc.check_permission("write")
    if action not in DECISION_OPTIONS:
        frappe.throw("Invalid human decision")
    if not rationale:
        frappe.throw("Human decision rationale required")


def save_human_action(doc, method=None):
    action = (doc.get("js_human_action") or "").strip()
    if not action:
        return
    # Frappe ORM enforces the human approver role and captures the real actor.
    frappe.get_doc({
        "doctype": "Job Search Decision", "opportunity": doc.name,
        "decision": action, "rationale": doc.js_human_action_rationale,
    }).insert()
    # Clear the one-shot form inputs; the immutable Decision document persists.
    doc.db_set("js_human_action", "", update_modified=False)
    doc.db_set("js_human_action_rationale", "", update_modified=False)
