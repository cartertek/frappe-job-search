"""Shared validation and business operations; API functions stay thin."""

import frappe
from frappe.utils import now_datetime, nowdate

from job_search.permissions import require_doc, require_operator, require_opportunity
from job_search.postings import capture_posting
from job_search.workflow import require_decision, status_name


def register_opportunity(*, employer, title, source_url=None, description=None, requisition_id=None,
                         location=None, source_name="Employer website"):
    require_operator()
    employer = (employer or "").strip()
    title = (title or "").strip()
    if not employer or not title or not (source_url or description):
        frappe.throw("Employer, title, and a posting URL or description are required")
    existing_org = frappe.db.exists("CRM Organization", {"organization_name": employer})
    if existing_org:
        org = require_doc("CRM Organization", existing_org, "read")
    else:
        org = frappe.get_doc({"doctype": "CRM Organization", "organization_name": employer})
        org.insert()
    if source_url:
        existing = frappe.db.get_value("Job Search Posting", {"source_url": source_url}, "opportunity")
        if not existing:
            # A URL-only first observation is a discovery source, not a captured posting.
            # Re-import with description must reuse its Deal instead of duplicating it.
            existing = frappe.db.get_value("Job Search Source", {"url": source_url}, "opportunity")
        if existing:
            deal = require_opportunity(existing, "read")
            if deal.organization != org.name:
                frappe.throw("Posting URL belongs to a different employer; review this duplicate")
            captured = (capture_posting(deal.name, description=description,
                source_name=source_name, source_url=source_url, posting_title=title,
                requisition_id=requisition_id) if description else None)
            return {"opportunity": deal.name, "organization": org.name, "created": False,
                    "posting": captured["posting"] if captured else None,
                    "snapshot_created": captured["created"] if captured else False,
                    "possible_duplicates": []}
    # Strict match. Never merge on title alone or a requisition ID alone.
    candidate_filters = {"organization": org.name, "js_is_job_search": 1}
    candidates = frappe.get_all("CRM Deal", filters=candidate_filters,
                                fields=["name", "js_job_title", "js_requisition_id", "js_location"])
    strict = [x for x in candidates if requisition_id and x.js_requisition_id == requisition_id
              and x.js_job_title.casefold() == title.casefold()
              and (x.js_location or "").casefold() == (location or "").casefold()]
    if len(strict) == 1:
        deal = require_opportunity(strict[0].name, "write")
        created = False
    else:
        deal = frappe.get_doc({
            "doctype": "CRM Deal", "organization": org.name, "lead_name": title,
            "status": status_name("Discovered"), "js_is_job_search": 1,
            "js_job_title": title, "js_requisition_id": requisition_id,
            "js_posting_url": source_url, "js_location": location,
            "js_discovered_on": nowdate(), "js_stage": "Discovered",
        })
        deal.insert()
        created = True
    posting = None
    if description:
        posting = capture_posting(deal.name, description=description, source_name=source_name,
            source_url=source_url, posting_title=title, requisition_id=requisition_id)
    elif source_url and not frappe.db.exists(
        "Job Search Source", {"url": source_url, "opportunity": deal.name}
    ):
        frappe.get_doc({
            "doctype": "Job Search Source", "title": f"{title} (discovery)",
            "url": source_url, "source_type": "Job Board",
            "retrieved_on": now_datetime(), "opportunity": deal.name,
            "organization": org.name, "verification_status": "Unverified",
        }).insert()
    return {
        "opportunity": deal.name, "organization": org.name,
        "posting": posting["posting"] if posting else None, "created": created,
        "possible_duplicates": [x.name for x in candidates if x.name != deal.name and
                                (x.js_job_title or "").casefold() == title.casefold()],
    }


def start_procedure(procedure, opportunity=None, organization=None, operator=None):
    require_operator()
    proc = require_doc("Job Search Procedure", procedure)
    if proc.status != "Active":
        frappe.throw("Only published active procedure versions may be executed")
    if not opportunity and not organization:
        frappe.throw("An opportunity or organization is required")
    if opportunity:
        deal = require_opportunity(opportunity)
        organization = organization or deal.organization
        if deal.organization != organization:
            frappe.throw("Organization does not match opportunity")
    exec_doc = frappe.get_doc({
        "doctype": "Job Search Procedure Execution", "procedure": proc.name,
        "procedure_version": proc.version, "opportunity": opportunity,
        "organization": organization, "operator": operator or frappe.session.user,
        "status": "In Progress", "started_at": now_datetime(),
        "steps": [{"step_id": s.step_id, "title": s.title, "status": "Pending"} for s in proc.steps],
    })
    exec_doc.insert()
    return exec_doc.name


def complete_step(execution, step_id, *, findings="", produced_records=""):
    require_operator()
    doc = require_doc("Job Search Procedure Execution", execution, "write")
    if doc.status != "In Progress":
        frappe.throw("Only in-progress executions can be updated")
    step = next((s for s in doc.steps if s.step_id == step_id), None)
    if not step:
        frappe.throw("Unknown procedure step")
    step.status = "Completed"
    step.findings = findings
    step.produced_records = produced_records
    step.completed_on = now_datetime()
    step.completed_by = frappe.session.user
    doc.save()
    return doc.name


def complete_procedure(execution, *, assessment):
    require_operator()
    doc = require_doc("Job Search Procedure Execution", execution, "write")
    if doc.status != "In Progress":
        frappe.throw("Execution is not in progress")
    procedure = require_doc("Job Search Procedure", doc.procedure)
    completed = {s.step_id for s in doc.steps if s.status == "Completed"}
    missing = [s.step_id for s in procedure.steps if s.required and s.step_id not in completed]
    if missing:
        frappe.throw("Required steps incomplete: " + ", ".join(missing))
    if not (assessment or "").strip():
        frappe.throw("Completion assessment is required")
    doc.assessment = assessment
    doc.status = "Completed"
    doc.completed_at = now_datetime()
    doc.save()
    return doc.name


def record_application(opportunity, *, submission_method, submitted_on, authorization,
                       materials=None, resume=None, cover_letter=None, reference_number=None,
                       confirmation=None, submission_url=None):
    require_operator()
    require_opportunity(opportunity, "write")
    require_decision(opportunity, "Authorize Application", authorization)
    if not (materials or resume or cover_letter):
        frappe.throw("Identify the submitted materials")
    if not confirmation and not reference_number:
        frappe.throw("Submission confirmation or a reference number is required")
    if reference_number:
        existing = frappe.db.get_value("Job Search Application", {
            "opportunity": opportunity, "reference_number": reference_number}, "name")
        if existing:
            return existing
    application = frappe.get_doc({
        "doctype": "Job Search Application", "opportunity": opportunity,
        "submission_method": submission_method, "submitted_on": submitted_on,
        "authorization": authorization, "materials": materials,
        "resume": resume, "cover_letter": cover_letter, "reference_number": reference_number,
        "confirmation": confirmation, "submission_url": submission_url, "status": "Submitted",
    })
    application.insert()
    deal = require_opportunity(opportunity, "write")
    deal.js_latest_application = application.name
    deal.js_applied_on = submitted_on
    deal.save()
    return application.name


def record_interview(opportunity, *, interview_type, application=None, scheduled_at=None,
                     timezone=None, round=None, interviewers=None, notes=None):
    require_operator()
    require_opportunity(opportunity, "write")
    doc = frappe.get_doc({
        "doctype": "Job Search Interview", "opportunity": opportunity, "application": application,
        "interview_type": interview_type, "scheduled_at": scheduled_at, "timezone": timezone,
        "round": round, "interviewers": [{"contact": c} for c in (interviewers or [])],
        "notes": notes, "outcome": "Pending",
    })
    doc.insert()
    deal = require_opportunity(opportunity, "write")
    deal.js_interview_schedule = (
        f"{interview_type} — {scheduled_at or 'not scheduled'} "
        f"({timezone or 'timezone not set'})"
    )
    deal.save()
    return doc.name
