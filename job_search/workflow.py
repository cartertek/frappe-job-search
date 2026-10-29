"""Job Search Opportunity stage invariants, independent of UI and REST mutation entrypoint."""

from html import escape

import frappe
from frappe.utils import now_datetime

from job_search.claim_validation import claim_field_errors, source_date_matches_search
from job_search.heuristics import COMPENSATION_HEURISTIC_ID, research_heuristics
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
DECISIONS = {"Qualified": "Pursue", "Applied": "Authorize Application",
             "Accepted": "Accept Offer"}


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


def _review_readiness_failures(deal):
    """All unmet requirements for a job to move to Ready to Review.

    The active search is a strict qualification gate. An explicit Include does not
    excuse a deterministic mismatch at this stage; the UI search results can still
    use overrides for discovery separately.
    """
    if not deal.active_job_search:
        return ["Active Job Search is required"]
    if not frappe.db.exists("Job Search Search", deal.active_job_search):
        return [f"Active Job Search {deal.active_job_search} does not exist"]

    search = frappe.get_doc("Job Search Search", deal.active_job_search)
    errors = []
    if not search.enabled:
        errors.append(f"Active Job Search {search.name} is disabled")
    errors.extend(match_failures(deal, search))

    if deal.globally_rejected:
        errors.append("Job is globally rejected")
    if frappe.db.get_value("Job Search Employer", deal.organization, "globally_rejected"):
        errors.append("Employer is globally rejected")
    override = next((row.override for row in search.overrides if row.job == deal.name), None)
    if override == "Exclude":
        errors.append("Job is explicitly excluded from the active job search")
    if search.require_heuristics and override != "Include":
        errors.append("Active job search requires an explicit Include override")

    defined = {row["name"]: row["heuristic_name"] for row in research_heuristics(search)}
    required = {identifier: name for identifier, name in defined.items()
                if identifier != COMPENSATION_HEURISTIC_ID or deal.compensation_not_given}
    valid_claims = {identifier: 0 for identifier in required}
    for row in deal.research_heuristics:
        identifier = row.heuristic_id
        if identifier not in defined:
            errors.append(f"Unexpected heuristic claim: {row.heuristic_name or identifier or '(unnamed)'}")
            continue
        if row.heuristic_name != defined[identifier]:
            errors.append(f"Heuristic claim name does not match configured heuristic: {row.heuristic_name}")
            continue
        quote = (getattr(row, 'quote', None) or '').strip()
        source = (getattr(row, 'source', None) or '').strip()
        label = defined[identifier]
        if not quote or not source or not source.startswith(('https://', 'http://')):
            errors.append(f"Heuristic claim '{label}' requires an exact quote and a valid source URL")
        field_errors = claim_field_errors(row)
        errors.extend(f"Heuristic claim '{label}': {message}" for message in field_errors)
        if field_errors:
            continue
        if not source_date_matches_search(row.source_date, search.posted_after):
            errors.append(
                f"Heuristic claim '{label}' Source Date must be on or after "
                f"{search.posted_after}; None cannot meet a configured date cutoff"
            )
        elif quote and source and source.startswith(('https://', 'http://')) and identifier in valid_claims:
            valid_claims[identifier] += 1
    for identifier, name in required.items():
        if valid_claims[identifier] < 1:
            errors.append(f"Research heuristic '{name}' requires at least one sourced claim")
    return errors


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
        if errors:
            frappe.throw("Cannot move to Ready to Review:<ul>" + "".join(
                f"<li>{escape(message)}</li>" for message in errors
            ) + "</ul>")

    if next_stage == "Qualified":
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
    if next_stage == "Accepted" and not (deal.offer_details or "").strip():
        frappe.throw("Offer details are required")
    if next_stage in DECISIONS and next_stage not in ("Qualified", "Applied"):
        require_decision(deal.name, DECISIONS[next_stage], ctx.get("decision"))
    if previous == "Rejected" and next_stage == "Researching" and ctx.get("action") == "reopen":
        return ctx, override
    if previous in TERMINAL and next_stage == "Researching" and not override:
        frappe.throw("Reopening a terminal opportunity requires an approved exception")
    return ctx, override


def validate_deal(doc, method=None):
    # Frappe's 'reqd' property does not prevent whitespace-only Data / Small Text.
    # Validate both fields on every save, not only during Ready to Review.
    for row in doc.get("research_heuristics") or []:
        for message in claim_field_errors(row):
            frappe.throw(f"Heuristic claim '{row.heuristic_name or '(unnamed)'}': {message}")
    if doc.get("compensation_not_given"):
        for field in ("compensation_min", "compensation_max", "currency", "compensation_period"):
            doc.set(field, None)
    elif (doc.get("compensation_min") is None and doc.get("status") != "Rejected"
          and (getattr(frappe.flags, "job_search_transition_context", None) or {}).get("action") != "reopen"):
        frappe.throw("Minimum Compensation is required unless Compensation Not Given is checked")
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
