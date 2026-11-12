"""Opportunity stage invariants, independent of UI and REST mutation entrypoint."""

from html import escape

import frappe
from frappe.utils import now_datetime

from job_search.claim_validation import claim_field_errors, source_date_matches_search
from job_search.display import job_label
from job_search.heuristics import COMPENSATION_HEURISTIC_ID, research_heuristics
from job_search.recency import active_window_start
from job_search.searches import match_failures

STAGES = (
    "Discovered", "Researching", "Ready to Review", "Qualified",
    "Applied", "Interviewing", "Accepted", "Rejected",
)
TERMINAL = {"Accepted", "Rejected"}
TRANSITIONS = {
    "Discovered": {"Researching", "Rejected"},
    "Researching": {"Ready to Review", "Rejected"},
    "Ready to Review": {"Researching", "Qualified", "Rejected"},
    "Qualified": {"Applied", "Rejected"},
    "Applied": {"Interviewing", "Rejected"},
    "Interviewing": {"Accepted", "Rejected"},
    "Accepted": {"Rejected"},
    "Rejected": {"Researching"},
}
DECISIONS = {"Qualified": "Pursue", "Accepted": "Accept Offer"}


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
    """The research handoff needs an evidenced Opportunity research record."""
    findings = frappe.get_all("Job Search Research", filters={"opportunity": deal.name}, pluck="name")
    for name in findings:
        doc = frappe.get_doc("Job Search Research", name)
        if doc.evidence_class in ("Verified Fact", "Supported Interpretation") and doc.sources:
            return True
    return False


def _has_completed_research_procedure(deal):
    """A research/qualification procedure is completed before human review."""
    rows = frappe.get_all("Job Search Procedure Execution",
        filters={"opportunity": deal.name, "status": "Completed"},
        fields=["procedure"])
    return any(frappe.db.get_value("Job Search Procedure", x.procedure, "procedure_id")
               in ("research-employer", "research-opening", "qualify") for x in rows)


def _count(doctype, opportunity):
    return frappe.db.count(doctype, {"opportunity": opportunity})


def _job_readiness_failures(job, search):
    """Job-specific evidence gate. Shared evidence is allowed only where applicable."""
    errors = []
    if job.availability_status != "Active":
        errors.append(
            f"Job {job_label(job)} is not confirmed active "
            f"({job.availability_status or 'Unknown'})"
        )
    errors.extend(match_failures(job, search))
    if not job.job_description or not job.job_description.strip():
        errors.append("Full original Job Description is required")
    if not job.latest_posting:
        errors.append("A captured Job Posting is required")
    defined = {r["name"]: r["heuristic_name"] for r in research_heuristics(search)}
    required = {identifier: label for identifier, label in defined.items()
                if identifier != COMPENSATION_HEURISTIC_ID or job.compensation_not_given}
    valid = {identifier: 0 for identifier in required}
    activity_start = active_window_start(search.active_in_past_count, search.active_in_past_unit)
    for row in job.research_heuristics:
        identifier = row.heuristic_id
        if identifier not in defined or row.heuristic_name != defined[identifier]:
            errors.append(f"Unexpected or mismatched heuristic: {row.heuristic_name or identifier}")
            continue
        issues = claim_field_errors(row)
        quote = (getattr(row, 'quote', None) or '').strip()
        source = (getattr(row, 'source', None) or '').strip()
        if not quote or not source.startswith(('http://','https://')):
            issues.append('requires an exact quote and a valid source URL')
        errors.extend(f"Heuristic {row.heuristic_name}: {msg}" for msg in issues)
        if issues:
            continue
        if not source_date_matches_search(row.source_date, activity_start):
            errors.append(f"Heuristic {row.heuristic_name}: source date outside active window")
            continue
        if identifier in valid and quote and source.startswith(('http://', 'https://')):
            valid[identifier] += 1
    for identifier, label in required.items():
        if not valid[identifier]:
            errors.append(f"Research heuristic '{label}' requires at least one sourced claim")
    return errors


def _review_readiness_failures(deal):
    """An Opportunity qualifies for a Search if at least one associated Job qualifies."""
    if not deal.active_job_search:
        return ["Active Job Search is required"]
    if not frappe.db.exists("Job Search Search", deal.active_job_search):
        return ["Active Job Search does not exist"]
    search = frappe.get_doc("Job Search Search", deal.active_job_search)
    errors = []
    if not search.enabled:
        errors.append("Active Job Search is disabled")
    if deal.globally_rejected:
        errors.append("Opportunity is globally rejected")
    if frappe.db.get_value("Job Search Employer", deal.organization, "globally_rejected"):
        errors.append("Organization is globally rejected")
    override = next((r.override for r in search.overrides
                     if r.opportunity == deal.name), None)
    if override == "Exclude":
        errors.append("Opportunity is excluded from the Active Job Search")
    if search.require_heuristics and override != "Include":
        errors.append("Active Job Search requires an explicit Include for this Opportunity")
    if errors:
        return errors
    if not deal.jobs:
        return ["At least one Job is required"]
    job_errors = []
    for row in deal.jobs:
        job = frappe.get_doc("Job", row.job)
        if job.organization != deal.organization:
            job_errors.append(f"Job {job_label(job)} belongs to another Organization")
            continue
        failures = _job_readiness_failures(job, search)
        if not failures:
            return []
        job_errors.extend(f"Job {job_label(job)}: {failure}" for failure in failures)
    return ["No associated Job currently qualifies for this Opportunity"] + job_errors[:20]


def _validate_transition(deal, previous, next_stage):
    if next_stage not in TRANSITIONS.get(previous, set()):
        frappe.throw(f"Unsupported Job Search transition: {previous} -> {next_stage}")

    ctx = getattr(frappe.flags, "job_search_transition_context", None) or {}
    override = None
    if ctx.get("deal") == deal.name and ctx.get("exception"):
        override = require_decision(deal.name, "Override", ctx.get("override_decision"))
        if not (ctx.get("reason") or "").strip():
            frappe.throw("An override must include a reason")

    if next_stage == "Ready to Review":
        errors = _review_readiness_failures(deal)
        if not _has_research(deal):
            errors.append("Cited Opportunity research is required before Ready to Review")
        if not _has_completed_research_procedure(deal):
            errors.append(
                "A completed research or qualification procedure is required before Ready to Review"
            )
        if errors:
            frappe.throw("Cannot move to Ready to Review:<ul>" + "".join(
                f"<li>{escape(message)}</li>" for message in errors
            ) + "</ul>")

    if next_stage == "Qualified":
        # Ready to Review is the final evidence gate. The actual human
        # approver decides whether to Pursue without additional validation.
        require_decision(deal.name, "Pursue", ctx.get("decision"))
    required_activity = {
        "Applied": "Application",
        "Interviewing": "Interview",
        "Accepted": "Acceptation",
    }.get(next_stage)
    if required_activity and not any(
        row.type == required_activity for row in deal.activity_log
    ):
        frappe.throw(f"{next_stage} requires an {required_activity} Activity Log entry")

    if next_stage == "Applied":
        # The human Mark Applied action and its dated Application activity are
        # the complete transition requirements. Detailed submission records and
        # separate Authorize Application decisions are optional historical data.
        from job_search.permissions import require_approver

        require_approver()  # Protect direct ORM / REST status writes as well.
    if next_stage == "Interviewing" and not _count("Job Search Interview", deal.name):
        frappe.throw("Interviewing requires an interview record")
    if next_stage == "Accepted" and not (deal.offer_details or "").strip():
        frappe.throw("Offer details are required")
    if next_stage in DECISIONS and next_stage not in ("Qualified", "Applied"):
        require_decision(deal.name, DECISIONS[next_stage], ctx.get("decision"))
    if previous == "Rejected" and next_stage == "Researching" and ctx.get("action") == "reopen":
        return ctx, override
    if previous in TERMINAL and next_stage == "Researching" and not override:
        frappe.throw("Reopening a terminal opportunity requires an approved exception")
    return ctx, override


def validate_job(doc, method=None):
    if not doc.organization or not (doc.job_title or '').strip():
        frappe.throw("A Job requires an Organization and Job Title")
    if doc.availability_status not in ("Unknown", "Active", "Closed", "Rejected"):
        frappe.throw("Invalid Job availability status")
    if doc.availability_status == "Rejected" and not (doc.job_rejection_reason or '').strip():
        frappe.throw("A rejected Job requires a rejection reason")
    if doc.compensation_not_given:
        for field in ("compensation_min", "compensation_max", "currency", "compensation_period"):
            doc.set(field, None)
    for row in doc.research_heuristics:
        for error in claim_field_errors(row):
            frappe.throw(f"Heuristic claim: {error}")


def validate_deal(doc, method=None):
    """Opportunity pursuit state is distinct from Job availability."""
    if not doc.organization or not (doc.opportunity_name or '').strip():
        frappe.throw("An Opportunity requires an Organization and name")
    linked = set()
    for row in doc.jobs:
        if row.job in linked:
            frappe.throw(f"Duplicate Job in Opportunity: {job_label(row.job)}")
        linked.add(row.job)
        if frappe.db.get_value("Job", row.job, "organization") != doc.organization:
            frappe.throw(f"Job {job_label(row.job)} does not belong to the Opportunity Organization")
    # Frappe displays child table rows in idx order, so normalize idx by Date
    # on every save. Equal dates retain their existing relative ordering.
    activities = sorted(doc.activity_log, key=lambda row: str(row.date or ''))
    for index, row in enumerate(activities, start=1):
        row.idx = index
    doc.activity_log = activities
    # The field is a database-synchronized, filterable snapshot, not a manual
    # pursuit status. Set it on ORM saves too so the in-memory document and
    # database agree even while Frappe is still persisting child rows.
    doc.applied = 1 if any(row.type == "Application" for row in activities) else 0
    before = doc.get_doc_before_save() if not doc.is_new() else None
    previous = before.status if before else None
    status = doc.status or (previous if previous else "Discovered")
    if status not in STAGES:
        frappe.throw("Invalid Opportunity status")
    if doc.is_new() and status != "Discovered":
        frappe.throw("A new Opportunity must begin in Discovered")
    doc.status = status
    if previous and previous != status:
        _validate_transition(doc, previous, status)
        if status == "Applied" and not doc.applied_on:
            dates = [row.date for row in doc.activity_log
                     if row.type == "Application" and row.date]
            if dates:
                doc.applied_on = max(dates)
    if not doc.active_job_search:
        doc.eligibility_status = "Unverified"
    else:
        doc.eligibility_status = "Eligible" if not _review_readiness_failures(doc) else "Needs Research"


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
