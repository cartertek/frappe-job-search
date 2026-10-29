"""Human-driven workflow actions and scoped rejection, enforced server-side."""

import frappe

from job_search.permissions import require_approver, require_operator, require_doc, require_opportunity
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
    if action in ("reject", "reopen", "ready_to_review", "needs_research"):
        require_operator()
    else:
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
    if action == "reopen":
        if job.status != "Rejected":
            frappe.throw("Only Rejected jobs can be reopened")
        if not rationale:
            frappe.throw("Reopening reason is required")
        if frappe.db.get_value("Job Search Employer", job.organization, "globally_rejected"):
            frappe.throw("The organization is globally rejected; resolve that rejection before reopening this Job")
        # Undo only this Job's rejection. Other search exclusions remain intact.
        if job.rejection_scope == "Search Only" and job.rejection_search:
            query = require_doc("Job Search Search", job.rejection_search, "write")
            for row in list(query.overrides):
                if row.job == job.name and row.override == "Exclude":
                    query.remove(row)
            query.save()
        job.globally_rejected = 0
        job.status = "Researching"
        previous_context = getattr(frappe.flags, "job_search_transition_context", None)
        frappe.flags.job_search_transition_context = {"deal": job.name, "action": "reopen", "reason": rationale}
        try:
            job.save()
        finally:
            frappe.flags.job_search_transition_context = previous_context
        job.add_comment("Comment", f"Reopened for research: {rationale}")
        return {"status": job.status, "opportunity": job.name}
    if action == "reject":
        if scope not in ("search", "job", "organization"):
            frappe.throw("Choose a rejection scope")
        if not rationale:
            frappe.throw("Rejection rationale is required")
        if scope == "search":
            search = search or job.active_job_search
            if not search:
                frappe.throw("Select a search or set the Job's Active Job Search before rejecting")
            query = require_doc("Job Search Search", search, "write")
            for row in list(query.overrides):
                if row.job == job.name:
                    query.remove(row)
            query.append("overrides", {"job": job.name, "override": "Exclude"})
            query.save()
            job.rejection_scope = "Search Only"
            job.rejection_search = search
            job.rejection_reason = rationale
            if job.status not in ("Rejected", "Accepted"):
                job.status = "Rejected"
            job.save()
        elif scope == "job":
            job.rejection_scope = "Job Globally"
            job.rejection_search = None
            job.rejection_reason = rationale
            job.globally_rejected = 1
            if job.status not in ("Rejected", "Accepted"):
                job.status = "Rejected"
            job.save()
        else:
            employer = require_doc("Job Search Employer", job.organization, "write")
            employer.globally_rejected = 1
            employer.save()
            job.rejection_scope = "Entire Organization"
            job.rejection_search = None
            job.rejection_reason = rationale
            # The initiating Job must also visibly reflect its rejection.
            if job.status not in ("Rejected", "Accepted"):
                job.status = "Rejected"
            job.save()
        # Research rejection is an operator action, not a human authorization.
        # Record its rationale under the actual signed-in actor, without creating
        # a Job Search Decision (which requires an approver).
        job.add_comment("Comment", f"Research rejection ({scope}): {rationale}")
        return {"status": job.status, "scope": scope}
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
