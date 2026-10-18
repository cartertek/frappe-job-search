"""Documented operator endpoints. Ordinary CRUD also uses /api/resource/<DocType>."""

from contextlib import contextmanager

import frappe
from frappe.utils import now_datetime

from job_search import services
from job_search.permissions import (
    require_approver,
    require_doc,
    require_operator,
    require_opportunity,
)
from job_search.postings import capture_posting as capture_posting_record
from job_search.queues import follow_up_queue, research_queue
from job_search.workflow import STAGES


def success(data=None, warnings=None):
    return {"ok": True, "data": data or {}, "warnings": warnings or [], "messages": []}


def failure(code, message, details=None):
    return {"ok": False, "error": {"code": code, "message": message, "details": details or {}}}


def _data(value):
    if isinstance(value, str):
        return frappe.parse_json(value)
    return value or {}


@contextmanager
def _transition_context(value):
    previous = getattr(frappe.flags, "job_search_transition_context", None)
    frappe.flags.job_search_transition_context = value
    try:
        yield
    finally:
        frappe.flags.job_search_transition_context = previous


@frappe.whitelist()
def register_opportunity(employer, title, source_url=None, description=None,
                         requisition_id=None, location=None, source_name="Employer website"):
    return success(services.register_opportunity(
        employer=employer, title=title, source_url=source_url, description=description,
        requisition_id=requisition_id, location=location, source_name=source_name,
    ))


@frappe.whitelist()
def capture_posting(opportunity, description, source_name, source_url=None,
                    posting_title=None, requisition_id=None, snapshot=None):
    return success(capture_posting_record(
        opportunity, description=description, source_name=source_name,
        source_url=source_url, posting_title=posting_title,
        requisition_id=requisition_id, snapshot=snapshot,
    ))


@frappe.whitelist()
def add_research(title, evidence_class, content, category="General Observations",
                 opportunity=None, organization=None, sources=None, procedure_execution=None):
    require_operator()
    if not opportunity and not organization:
        frappe.throw("Research must relate to an employer or opportunity")
    if opportunity:
        deal = require_opportunity(opportunity, "read")
        organization = organization or deal.organization
        if organization != deal.organization:
            frappe.throw("Research employer differs from opportunity employer")
    links = []
    for item in _data(sources) or []:
        if isinstance(item, str):
            require_doc("Job Search Source", item)
            links.append({"source": item})
            continue
        if not isinstance(item, dict):
            frappe.throw("Sources must be existing names or source dictionaries")
        if item.get("name"):
            require_doc("Job Search Source", item["name"])
            links.append({"source": item["name"]})
        else:
            source = frappe.get_doc({"doctype": "Job Search Source",
                "title": item.get("title"), "url": item.get("url"),
                "archive": item.get("archive"),
                "source_type": item.get("source_type") or "Other",
                "excerpt": item.get("excerpt"),
                "publisher": item.get("publisher"),
                "organization": organization, "opportunity": opportunity,
                "verification_status": item.get("verification_status") or "Unverified",
                "retrieved_on": now_datetime(),
            }).insert()
            links.append({"source": source.name})
    record = frappe.get_doc({
        "doctype": "Job Search Research", "title": title, "content": content,
        "category": category, "evidence_class": evidence_class,
        "status": "Draft", "operator": frappe.session.user,
        "organization": organization, "opportunity": opportunity,
        "procedure_execution": procedure_execution, "sources": links,
    }).insert()
    return success({"research": record.name, "sources": [x["source"] for x in links]})


@frappe.whitelist()
def start_procedure(procedure, opportunity=None, organization=None, operator=None):
    return success({"execution": services.start_procedure(
        procedure, opportunity=opportunity, organization=organization, operator=operator,
    )})


@frappe.whitelist()
def complete_procedure_step(execution, step_id, findings="", produced_records=""):
    return success({"execution": services.complete_step(
        execution, step_id, findings=findings, produced_records=produced_records,
    )})


@frappe.whitelist()
def complete_procedure(execution, assessment):
    return success({"execution": services.complete_procedure(execution, assessment=assessment)})


@frappe.whitelist()
def authorize_decision(opportunity, decision, rationale):
    """Only an actual signed-in approver can issue approval; operators cannot impersonate one."""
    require_approver()
    require_opportunity(opportunity, "read")
    doc = frappe.get_doc({"doctype": "Job Search Decision",
                          "opportunity": opportunity, "decision": decision,
                          "rationale": rationale}).insert()
    return success({"decision": doc.name, "authorized_by": doc.authorized_by})


@frappe.whitelist()
def transition_opportunity(opportunity, stage, reason="", decision=None,
                           exception=None, override_decision=None):
    require_operator()
    if stage not in STAGES:
        frappe.throw("Invalid Job Search stage")
    deal = require_opportunity(opportunity, "write")
    if stage == deal.js_stage:
        return success({"opportunity": deal.name, "stage": deal.js_stage, "changed": False})
    with _transition_context({
        "deal": opportunity, "decision": decision, "reason": reason,
        "exception": exception, "override_decision": override_decision,
    }):
        deal.js_stage = stage
        deal.save()  # CRM Deal validation hook protects every UI/REST save path.
    return success({"opportunity": deal.name, "stage": deal.js_stage, "changed": True})


@frappe.whitelist()
def record_application(opportunity, submission_method, submitted_on, authorization,
                       materials=None, resume=None, cover_letter=None, reference_number=None,
                       confirmation=None, submission_url=None):
    name = services.record_application(
        opportunity, submission_method=submission_method, submitted_on=submitted_on,
        authorization=authorization, materials=materials, resume=resume,
        cover_letter=cover_letter, reference_number=reference_number,
        confirmation=confirmation, submission_url=submission_url,
    )
    return success({"application": name})


@frappe.whitelist()
def record_interview(opportunity, interview_type, application=None, scheduled_at=None,
                     timezone=None, round=None, interviewers=None, notes=None):
    return success({"interview": services.record_interview(
        opportunity, interview_type=interview_type, application=application,
        scheduled_at=scheduled_at, timezone=timezone, round=round,
        interviewers=_data(interviewers), notes=notes,
    )})


@frappe.whitelist()
def create_follow_up(opportunity, title, due_date, assigned_to=None, description=None):
    require_operator()
    require_opportunity(opportunity, "write")
    task = frappe.get_doc({
        "doctype": "CRM Task", "title": title, "due_date": due_date,
        "assigned_to": assigned_to or frappe.session.user, "status": "Todo",
        "priority": "Medium", "description": description,
        "reference_doctype": "CRM Deal", "reference_docname": opportunity,
    }).insert()
    return success({"task": task.name})


@frappe.whitelist()
def get_follow_up_queue(horizon=14):
    return success(follow_up_queue(horizon))


@frappe.whitelist()
def get_research_queue(stale_after_days=90):
    return success(research_queue(stale_after_days))


@frappe.whitelist()
def get_work_queue():
    require_operator()
    deals = frappe.get_list("CRM Deal", filters={"js_is_job_search": 1},
        fields=["name", "organization", "js_job_title", "js_stage", "js_next_action_on",
                "js_deadline", "js_priority", "js_qualification"], limit_page_length=500)
    tasks = frappe.get_list("CRM Task", filters={"reference_doctype": "CRM Deal",
        "status": ["not in", ["Done", "Canceled"]]},
        fields=["name", "title", "due_date", "reference_docname", "status"],
        limit_page_length=500)
    ids = {d.name for d in deals}
    tasks = [x for x in tasks if x.reference_docname in ids]
    executions = frappe.get_list("Job Search Procedure Execution",
        filters={"status": ["in", ["Pending", "In Progress", "Blocked"]]},
        fields=["name", "opportunity", "organization", "status", "procedure"],
        limit_page_length=500)
    return success({"opportunities": deals, "tasks": tasks, "executions": executions})


@frappe.whitelist()
def get_company_dossier(organization):
    require_operator()
    company = require_doc("CRM Organization", organization)
    deals = frappe.get_list("CRM Deal", filters={
        "organization": company.name, "js_is_job_search": 1,
    }, fields=["name", "js_job_title", "js_stage", "js_qualification", "js_next_action_on"],
        limit_page_length=500)
    postings = frappe.get_list("Job Search Posting", filters={"organization": company.name},
        fields=["name", "opportunity", "posting_title", "retrieved_on", "status"],
        limit_page_length=500)
    research = frappe.get_list("Job Search Research", filters={"organization": company.name},
        fields=["name", "opportunity", "title", "status", "last_verified"],
        limit_page_length=500)
    sources = frappe.get_list("Job Search Source", filters={"organization": company.name},
        fields=["name", "opportunity", "title", "url", "verification_status"],
        limit_page_length=500)
    return success({"organization": company.as_dict(), "opportunities": deals,
                    "postings": postings, "research": research, "sources": sources})


@frappe.whitelist()
def get_opportunity_context(opportunity):
    require_operator()
    deal = require_opportunity(opportunity)
    employer = require_doc("CRM Organization", deal.organization)
    related = {}
    for key, doctype in (
        ("postings", "Job Search Posting"), ("research", "Job Search Research"),
        ("sources", "Job Search Source"), ("applications", "Job Search Application"),
        ("interviews", "Job Search Interview"),
        ("executions", "Job Search Procedure Execution"),
        ("decisions", "Job Search Decision"), ("transitions", "Job Search Transition"),
    ):
        related[key] = frappe.get_list(doctype, filters={"opportunity": opportunity},
                                       fields=["name", "modified"], limit_page_length=500)
    return success({"deal": deal.as_dict(), "employer": employer.as_dict(), **related})


@frappe.whitelist()
def publish_human_review(opportunity, posting_digest=None, research_digest=None,
                         recommendation=None, application_review=None, interview_brief=None):
    """Agent writes the human-facing summary to the CRM Deal Data tab.

    Only explicitly supported review fields are changed, never stage or approvals.
    Existing values are preserved when an argument is omitted.
    """
    require_operator()
    deal = require_opportunity(opportunity, "write")
    updates = {
        "js_posting_digest": posting_digest,
        "js_research_digest": research_digest,
        "js_agent_recommendation": recommendation,
        "js_application_review": application_review,
        "js_interview_brief": interview_brief,
    }
    changed = []
    for name, value in updates.items():
        if value is not None:
            value = str(value)
            if len(value) > 50000:
                frappe.throw("Human review field exceeds 50,000 characters")
            deal.set(name, value)
            changed.append(name)
    if changed:
        deal.save()
    return success({"opportunity": deal.name, "updated_fields": changed})


@frappe.whitelist()
def get_human_action_queue():
    """Permission-scoped queue of open opportunities awaiting human review."""
    require_operator()
    rows = frappe.get_list("CRM Deal", filters={"js_is_job_search": 1},
        fields=["name", "organization", "js_job_title", "js_stage",
                "js_agent_recommendation", "js_application_review",
                "js_next_action_on", "js_deadline", "js_human_feedback"],
        limit_page_length=500)
    results = []
    for row in rows:
        if row.js_stage in ("Accepted", "Rejected", "Withdrawn", "Closed"):
            continue
        decisions = frappe.get_list("Job Search Decision", filters={"opportunity": row.name},
            fields=["decision"], limit_page_length=100)
        existing = {d.decision for d in decisions}
        needed = None
        if row.js_stage == "Researching" and row.js_agent_recommendation and not (
            "Pursue" in existing or "Decline" in existing
        ):
            needed = "Pursue or Decline"
        elif row.js_stage == "Preparing" and row.js_application_review and not (
            "Authorize Application" in existing or "Decline Application" in existing
        ):
            needed = "Authorize or Decline Application"
        elif row.js_stage == "Offer" and not (
            "Accept Offer" in existing or "Reject Offer" in existing
        ):
            needed = "Accept or Reject Offer"
        if needed:
            results.append({**row, "action_required": needed})
    return success({"queue": results})


@frappe.whitelist()
def request_human_review(opportunity, requested_action, reviewer, summary, due_date=None):
    """Create a CRM-native pending review and a task for an actual human approver."""
    require_operator()
    deal = require_opportunity(opportunity, "write")
    if not (summary or "").strip():
        frappe.throw("Human review request must explain what should be reviewed")
    if requested_action not in ("Pursue or Decline", "Authorize or Decline Application",
                                "Accept or Reject Offer", "Withdraw", "Override"):
        frappe.throw("Invalid human review request")
    reviewer_roles = set(frappe.get_roles(reviewer))
    if not {"Job Search Approver", "System Manager"}.intersection(reviewer_roles):
        frappe.throw("Reviewer must have the human approver role", frappe.PermissionError)
    if not frappe.db.exists("User", {"name": reviewer, "enabled": 1}):
        frappe.throw("Reviewer must be an enabled user")
    if deal.js_review_status == "Pending":
        frappe.throw("This opportunity already has a pending human review")
    deal.js_review_request = requested_action
    deal.js_review_status = "Pending"
    deal.js_review_assigned_to = reviewer
    deal.js_agent_recommendation = summary
    deal.save()
    task = frappe.get_doc({
        "doctype": "CRM Task", "title": f"Human review: {deal.js_job_title}",
        "assigned_to": reviewer, "status": "Todo", "priority": "High",
        "due_date": due_date or deal.js_next_action_on or deal.js_deadline,
        "reference_doctype": "CRM Deal", "reference_docname": deal.name,
        "description": f"{requested_action}: {summary}. Review the CRM Deal Data tab, "
                       "then record a human decision and rationale.",
    }).insert()
    deal.js_review_task = task.name
    deal.save()
    return success({"opportunity": deal.name, "task": task.name,
                    "reviewer": reviewer, "requested_action": requested_action})
