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
def register_opportunity(employer, name=None):
    """Create or locate an organization-level Opportunity."""
    return success(services.register_opportunity(employer=employer, name=name))


@frappe.whitelist()
def register_job(employer, title, source_url=None, description=None,
                 requisition_id=None, location=None, source_name="Employer website", opportunity=None):
    return success(services.register_job(
        employer=employer,title=title,source_url=source_url,description=description,
        requisition_id=requisition_id,location=location,source_name=source_name,
        opportunity=opportunity))


@frappe.whitelist()
def capture_posting(job, description, source_name, source_url=None,
                    posting_title=None, requisition_id=None, snapshot=None, opportunity=None):
    return success(capture_posting_record(
        job,description=description,source_name=source_name,source_url=source_url,
        posting_title=posting_title,requisition_id=requisition_id,snapshot=snapshot,
        opportunity=opportunity))


@frappe.whitelist()
def add_research(title, evidence_class, content, category="General Observations",
                 opportunity=None, organization=None, sources=None, procedure_execution=None,
                 job=None):
    require_operator()
    if not opportunity and not organization and not job:
        frappe.throw("Research must relate to a Job, Opportunity, or Organization")
    if opportunity:
        deal = require_opportunity(opportunity, "read")
        organization = organization or deal.organization
        if organization != deal.organization:
            frappe.throw("Research employer differs from opportunity employer")
    if job:
        from job_search.opportunities import opportunities_for_job
        from job_search.permissions import require_job
        role=require_job(job,'read')
        if organization and role.organization != organization:
            frappe.throw('Job belongs to another Organization')
        organization=organization or role.organization
        if opportunity and opportunity not in opportunities_for_job(job):
            frappe.throw('Job is not associated with the selected Opportunity')
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
                "organization": organization, "opportunity": opportunity, "job": job,
                "verification_status": item.get("verification_status") or "Unverified",
                "retrieved_on": now_datetime(),
            }).insert()
            links.append({"source": source.name})
    record = frappe.get_doc({
        "doctype": "Job Search Research", "title": title, "content": content,
        "category": category, "evidence_class": evidence_class,
        "status": "Draft", "operator": frappe.session.user,
        "organization": organization, "opportunity": opportunity, "job": job,
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
    if stage == deal.status:
        return success({"opportunity": deal.name, "stage": deal.status, "changed": False})
    with _transition_context({
        "deal": opportunity, "decision": decision, "reason": reason,
        "exception": exception, "override_decision": override_decision,
    }):
        deal.status = stage
        deal.save()  # Opportunity validation hook protects every UI/REST save path.
    return success({"opportunity": deal.name, "stage": deal.status, "changed": True})


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
        "doctype": "Job Search Task", "title": title, "due_date": due_date,
        "assigned_to": assigned_to or frappe.session.user, "status": "Todo",
        "priority": "Medium", "description": description,
        "opportunity": opportunity,
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
    deals = frappe.get_list("Opportunity", filters={},
        fields=["name", "organization", "opportunity_name", "status", "next_action_on",
                "deadline", "priority"], limit_page_length=500)
    tasks = frappe.get_list("Job Search Task", filters={"status": ["not in", ["Done", "Canceled"]]},
        fields=["name", "title", "due_date", "opportunity", "status"],
        limit_page_length=500)
    ids = {d.name for d in deals}
    tasks = [x for x in tasks if x.opportunity in ids]
    executions = frappe.get_list("Job Search Procedure Execution",
        filters={"status": ["in", ["Pending", "In Progress", "Blocked"]]},
        fields=["name", "opportunity", "organization", "status", "procedure"],
        limit_page_length=500)
    return success({"opportunities": deals, "tasks": tasks, "executions": executions})


@frappe.whitelist()
def get_company_dossier(organization):
    require_operator()
    company = require_doc("Job Search Employer", organization)
    deals = frappe.get_list("Opportunity", filters={"organization": company.name},
        fields=["name", "opportunity_name", "status", "next_action_on"],
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
    jobs = frappe.get_list('Job', filters={'organization':company.name},
        fields=['name','job_title','availability_status'],limit_page_length=500)
    return success({"organization": company.as_dict(), "opportunities": deals,
                    "jobs":jobs,"postings": postings, "research": research, "sources": sources})


@frappe.whitelist()
def get_opportunity_context(opportunity):
    require_operator()
    deal = require_opportunity(opportunity)
    employer = require_doc("Job Search Employer", deal.organization)
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
    job_names = [row.job for row in deal.jobs] or ['__none__']
    related['jobs'] = frappe.get_list(
        'Job', filters={'name': ['in', job_names]},
        fields=['name', 'job_title', 'availability_status'], limit_page_length=500,
    )
    return success({"opportunity": deal.as_dict(), "employer": employer.as_dict(), **related})


@frappe.whitelist()
def publish_human_review(opportunity, posting_digest=None, research_digest=None,
                         recommendation=None, application_review=None, interview_brief=None,
                         job_description=None, research_findings=None,
                         research_recommendation=None, application_materials_for_review=None,
                         interview_preparation=None):
    """Agent writes the human-facing summary to the Opportunity Data tab.

    Only explicitly supported review fields are changed, never stage or approvals.
    Existing values are preserved when an argument is omitted.
    """
    require_operator()
    deal = require_opportunity(opportunity, "write")
    if job_description is not None or posting_digest is not None:
        # Job descriptions are job-specific; never place them on the Opportunity.
        frappe.throw('Publish a Job description on the Job record or capture its Posting')
    updates = {
        "research_findings": research_findings if research_findings is not None else research_digest,
        "research_recommendation": research_recommendation
        if research_recommendation is not None
        else recommendation,
        "application_materials_for_review": application_materials_for_review
        if application_materials_for_review is not None
        else application_review,
        "interview_preparation": interview_preparation
        if interview_preparation is not None
        else interview_brief,
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
    """Pending review tasks, rather than a duplicate status on each Job."""
    require_operator()
    tasks = frappe.get_list("Job Search Task", filters={
        "status": ["not in", ["Done", "Canceled"]],
        "title": ["like", "Human review:%"],
    }, fields=["name", "opportunity", "assigned_to", "title", "status", "due_date"],
        limit_page_length=500)
    return success({"queue": tasks})


@frappe.whitelist()
def request_human_review(opportunity, requested_action, reviewer, summary, due_date=None):
    """Create a native review task and assignment without another Job status."""
    require_operator()
    deal = require_opportunity(opportunity, "write")
    if not (summary or "").strip():
        frappe.throw("Human review request must explain what should be reviewed")
    if requested_action not in ("Pursue or Decline", "Authorize or Decline Application",
                                "Accept or Reject Offer", "Withdraw", "Override"):
        frappe.throw("Invalid human review request")
    if not {"Job Search Approver", "System Manager"}.intersection(frappe.get_roles(reviewer)):
        frappe.throw("Reviewer must have the human approver role", frappe.PermissionError)
    if not frappe.db.exists("User", {"name": reviewer, "enabled": 1}):
        frappe.throw("Reviewer must be an enabled user")
    task = frappe.get_doc({
        "doctype": "Job Search Task", "title": f"Human review: {deal.opportunity_name}",
        "assigned_to": reviewer, "status": "Todo", "priority": "High",
        "due_date": due_date or deal.next_action_on or deal.deadline,
        "opportunity": deal.name,
        "description": f"{requested_action}: {summary}",
    }).insert()
    from frappe.desk.form.assign_to import add as assign_deal

    assign_deal({
        "doctype": "Opportunity", "name": deal.name, "assign_to": [reviewer],
        "description": f"Job Search human review: {requested_action}",
    })
    return success({"opportunity": deal.name, "task": task.name,
                    "reviewer": reviewer, "requested_action": requested_action})


@frappe.whitelist()
def record_human_decision(opportunity, decision, rationale):
    """Persist the actual signed-in approver's immutable decision."""
    require_approver()
    deal = require_opportunity(opportunity, "write")
    if not (rationale or "").strip():
        frappe.throw("Decision rationale required")
    from job_search.human import DECISION_OPTIONS

    if decision not in DECISION_OPTIONS:
        frappe.throw("Invalid human decision")
    record = frappe.get_doc({
        "doctype": "Job Search Decision", "opportunity": deal.name,
        "decision": decision, "rationale": rationale.strip(),
    }).insert()
    deal.db_set("last_decision_record", record.name, update_modified=False)
    deal.db_set("last_decision", f"{decision}: {rationale.strip()}"[:1000], update_modified=False)
    # Close only review work assigned to this actual approver.
    tasks = frappe.get_list("Job Search Task", filters={
        "opportunity": deal.name, "assigned_to": frappe.session.user,
        "status": ["not in", ["Done", "Canceled"]], "title": ["like", "Human review:%"],
    }, pluck="name")
    for name in tasks:
        task = frappe.get_doc("Job Search Task", name)
        task.status = "Done"
        task.save()
    return success({"opportunity": deal.name, "decision": record.name, "stage": deal.status})


@frappe.whitelist()
def get_search_results(search):
    from job_search.searches import matching_jobs

    return success({'search':search,'opportunities':matching_jobs(search)})


@frappe.whitelist()
def set_search_membership(search, opportunity, override):
    from job_search.searches import set_membership

    return success(set_membership(search, opportunity, override))


@frappe.whitelist()
def reject_job(job, reason):
    from job_search.opportunities import reject_job as reject
    return success(reject(job, reason))


@frappe.whitelist()
def reopen_job(job, reason):
    from job_search.opportunities import reopen_job as reopen
    return success(reopen(job, reason))


@frappe.whitelist()
def associate_job(opportunity, job):
    from job_search.opportunities import associate_job as attach
    return success(attach(opportunity, job))


@frappe.whitelist()
def reject_organization(organization, reason):
    from job_search.searches import reject_employer
    return success({'organization':reject_employer(organization,reason)})


@frappe.whitelist()
def reopen_organization(organization, reason):
    from job_search.opportunities import reopen_organization as reopen
    return success(reopen(organization,reason))


@frappe.whitelist()
def perform_opportunity_action(opportunity, action, rationale=None, scope=None, search=None,
                               offer_details=None, activity=None):
    from job_search.workflow_actions import perform_action

    return success(perform_action(opportunity, action, rationale, scope, search,
                                  offer_details, activity))


@frappe.whitelist()
def get_search_research_strategies(search):
    """Return assigned strategies in execution order, with full instructions."""
    from job_search.strategies import get_search_strategies
    return success({"search": search, "strategies": get_search_strategies(search)})


@frappe.whitelist()
def get_job_active_searches(job):
    """Read Active Job Searches from the Opportunity(s) containing this Job."""
    from job_search.opportunities import opportunities_for_job
    from job_search.permissions import require_doc

    require_doc('Job', job, 'read')
    opportunities = opportunities_for_job(job)
    rows = frappe.get_all('Opportunity',
        filters={'name': ['in', opportunities or ['__none__']]},
        fields=['name','opportunity_name','active_job_search'],limit_page_length=100000)
    searches = [{'opportunity': row.name,'search':row.active_job_search}
                for row in rows if row.active_job_search]
    return success({'job':job,'searches':searches})
