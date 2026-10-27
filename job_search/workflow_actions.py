"""Human-driven workflow actions and scoped rejection, enforced server-side."""

import frappe

from job_search.permissions import require_approver, require_doc, require_opportunity
from job_search.workflow import _has_completed_research_procedure, _has_research


def _decision(job, action, rationale):
    decision = frappe.get_doc({
        "doctype": "Job Search Decision", "opportunity": job.name,
        "decision": action, "rationale": rationale,
    }).insert()
    job.db_set("last_decision_record", decision.name, update_modified=False)
    job.db_set("last_decision", f"{action}: {rationale}"[:1000], update_modified=False)
    return decision


def perform_action(opportunity, action, rationale=None, scope=None, search=None, offer_details=None):
    require_approver()
    job = require_opportunity(opportunity, "write")
    rationale = (rationale or "").strip()
    allowed = {
        "Researching": {"ready_to_review"},
        "Ready to Review": {"needs_research", "qualify"},
        "Qualified": {"mark_applied"},
        "Applied": {"begin_interviewing"},
        "Interviewing": {"accept_offer"},
    }
    if action == "reject":
        if scope not in ("search", "job", "organization"):
            frappe.throw("Choose a rejection scope")
        if not rationale:
            frappe.throw("Rejection rationale is required")
        if scope == "search":
            if not search:
                frappe.throw("Select the search to exclude this job from")
            query = require_doc("Job Search Search", search, "write")
            for row in list(query.overrides):
                if row.job == job.name:
                    query.remove(row)
            query.append("overrides", {"job": job.name, "override": "Exclude"})
            query.save()
        elif scope == "job":
            job.globally_rejected = 1
            if job.status not in ("Rejected", "Accepted"):
                job.status = "Rejected"
                job.save()
        else:
            employer = require_doc("Job Search Employer", job.organization, "write")
            employer.globally_rejected = 1
            employer.save()
        decision = _decision(job, "Decline", f"Scope: {scope}; {rationale}")
        return {"status": job.status, "decision": decision.name, "scope": scope}
    if action not in allowed.get(job.status, set()):
        frappe.throw("Action is not available from this status")
    if action in ("qualify", "accept_offer") and not rationale:
        frappe.throw("Decision rationale is required")
    target = {
        "ready_to_review": "Ready to Review",
        "needs_research": "Researching", "qualify": "Qualified",
        "mark_applied": "Applied", "begin_interviewing": "Interviewing",
        "accept_offer": "Accepted",
    }[action]
    if action == "qualify":
        if not (_has_research(job) and _has_completed_research_procedure(job)):
            frappe.throw("Complete cited research and a research procedure before qualifying")
        job.qualification = "Pursue"
        job.qualification_rationale = rationale
        _decision(job, "Pursue", rationale)
    elif action == "accept_offer":
        if offer_details:
            job.offer_details = offer_details
        if not (job.offer_details or "").strip():
            frappe.throw("Offer details are required")
        _decision(job, "Accept Offer", rationale)
    # Mark Applied requires a recorded submission; Begin Interviewing requires an interview.
    # Existing validation hooks enforce both, including for direct API calls.
    job.status = target
    job.save()
    return {"status": target, "opportunity": job.name}
