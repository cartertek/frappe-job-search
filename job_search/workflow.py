"""Job Search Opportunity stage invariants, independent of UI and REST mutation entrypoint."""

import frappe
from frappe.utils import now_datetime

STAGES = (
    "Discovered", "Researching", "Qualified", "Preparing", "Applied",
    "Screening", "Interviewing", "Offer", "Accepted", "Rejected", "Withdrawn", "Closed",
)
TERMINAL = {"Accepted", "Rejected", "Withdrawn", "Closed"}
TRANSITIONS = {
    "Discovered": {"Researching", "Closed", "Withdrawn"},
    "Researching": {"Qualified", "Closed", "Withdrawn"},
    "Qualified": {"Preparing", "Closed", "Withdrawn"},
    "Preparing": {"Applied", "Closed", "Withdrawn"},
    "Applied": {"Screening", "Interviewing", "Offer", "Rejected", "Withdrawn", "Closed"},
    "Screening": {"Interviewing", "Offer", "Rejected", "Withdrawn", "Closed"},
    "Interviewing": {"Offer", "Rejected", "Withdrawn", "Closed"},
    "Offer": {"Accepted", "Rejected", "Withdrawn", "Closed"},
    "Accepted": {"Closed"},
    "Rejected": {"Researching", "Closed"},
    "Withdrawn": {"Researching", "Closed"},
    "Closed": {"Researching"},
}
DECISIONS = {"Qualified": "Pursue", "Applied": "Authorize Application",
             "Accepted": "Accept Offer", "Withdrawn": "Withdraw"}


def _decision(opportunity, decision, requested=None):
    if requested:
        found = frappe.db.get_value(
            "Job Search Decision", requested, ["opportunity", "decision"], as_dict=True
        )
        if not found or found.opportunity != opportunity or found.decision != decision:
            frappe.throw(f"A matching {decision} approval is required")
        return requested
    return frappe.db.get_value("Job Search Decision", {
        "opportunity": opportunity, "decision": decision,
    }, "name", order_by="creation desc")


def require_decision(opportunity, kind, requested=None):
    name = _decision(opportunity, kind, requested)
    if not name:
        frappe.throw(f"Explicit {kind} authorization is required")
    return name


def _has_research(deal):
    # A research record must have evidence, not just unsupported prose.
    findings = frappe.get_all("Job Search Research", filters={"opportunity": deal.name}, pluck="name")
    for name in findings:
        doc = frappe.get_doc("Job Search Research", name)
        if doc.evidence_class in ("Verified Fact", "Supported Interpretation") and doc.sources:
            return True
    return False


def _has_completed_research_procedure(deal):
    rows = frappe.get_all("Job Search Procedure Execution",
        filters={"opportunity": deal.name, "status": "Completed"},
        fields=["procedure"])
    return any(frappe.db.get_value("Job Search Procedure", x.procedure, "procedure_id")
               in ("research-employer", "research-opening", "qualify") for x in rows)


def _count(doctype, opportunity):
    return frappe.db.count(doctype, {"opportunity": opportunity})


def _validate_transition(deal, previous, next_stage):
    if next_stage not in TRANSITIONS.get(previous, set()):
        frappe.throw(f"Unsupported Job Search transition: {previous} -> {next_stage}")

    ctx = getattr(frappe.flags, "job_search_transition_context", None) or {}
    override = None
    if ctx.get("deal") == deal.name and ctx.get("exception"):
        override = require_decision(deal.name, "Override", ctx.get("override_decision"))
        if not (ctx.get("reason") or "").strip():
            frappe.throw("An override must include a reason")

    if next_stage == "Qualified":
        if deal.qualification != "Pursue" or not (deal.qualification_rationale or "").strip():
            frappe.throw("Qualification decision and rationale are required")
        require_decision(deal.name, "Pursue", ctx.get("decision"))
        if not override and not (_has_research(deal) and _has_completed_research_procedure(deal)):
            frappe.throw(
                "Qualified requires cited research and a completed procedure or approved exception"
            )
    if next_stage == "Applied":
        require_decision(deal.name, "Authorize Application", ctx.get("decision"))
        if not _count("Job Search Application", deal.name):
            frappe.throw("Applied requires a saved, confirmed application submission")
        applications = frappe.get_all("Job Search Application",
            filters={"opportunity": deal.name},
            fields=["submitted_on", "resume", "cover_letter", "materials"],
        )
        if not any(a.submitted_on and (a.resume or a.cover_letter or a.materials) for a in applications):
            frappe.throw("Applied requires a submission date and identified application materials")
    if next_stage == "Interviewing" and not _count("Job Search Interview", deal.name):
        frappe.throw("Interviewing requires an interview record")
    if next_stage == "Offer" and not (deal.offer_details or "").strip():
        frappe.throw("Offer details are required")
    if next_stage in DECISIONS and next_stage not in ("Qualified", "Applied"):
        require_decision(deal.name, DECISIONS[next_stage], ctx.get("decision"))
    if next_stage == "Closed" and not (deal.closure_reason or "").strip():
        frappe.throw("Closure reason is required")
    if previous in TERMINAL and next_stage == "Researching" and not override:
        frappe.throw("Reopening a terminal opportunity requires an approved exception")
    return ctx, override


def validate_deal(doc, method=None):
    old = doc.get_doc_before_save() if not doc.is_new() else None
    if not doc.organization or not (doc.get("job_title") or "").strip():
        frappe.throw("A Job Search opportunity requires an employer and job title")
    old_stage = old.get("status") if old else None
    stage = doc.get("status") or ("Discovered" if not old else old_stage)
    # The standalone DocType owns its stage; status is read-only derived metadata.
    if stage not in STAGES:
        frappe.throw("Invalid Job Search status")
    if doc.is_new() and stage != "Discovered":
        frappe.throw("A new opportunity must begin in Discovered")
    doc.status = stage
    if old_stage and old_stage != stage:
        _validate_transition(doc, old_stage, stage)


def record_transition(doc, method=None):
    """Only server hooks can create a transition record; cover direct REST writes."""
    previous = doc.get_doc_before_save()
    old_stage = previous.get("status") if previous else ""
    new_stage = doc.get("status")
    if old_stage == new_stage:
        return
    ctx = getattr(frappe.flags, "job_search_transition_context", None) or {}
    authorization = ctx.get("decision") or ctx.get("override_decision")
    if new_stage in DECISIONS and not authorization:
        authorization = _decision(doc.name, DECISIONS[new_stage])
    transition = frappe.get_doc({
        "doctype": "Job Search Transition", "opportunity": doc.name,
        "from_stage": old_stage, "to_stage": new_stage,
        "actor": frappe.session.user, "transitioned_at": now_datetime(),
        "reason": ctx.get("reason", ""), "authorization": authorization,
        "exception": ctx.get("exception", ""),
    }).insert(ignore_permissions=True)  # Server-only immutable event, called after Deal validation.
    from job_search.tasks import create_stage_task

    create_stage_task(doc, transition)
