"""Shared validation and business operations; API functions stay thin."""

import frappe
from frappe.utils import now_datetime, nowdate

from job_search.permissions import require_doc, require_operator, require_opportunity
from job_search.postings import capture_posting
from job_search.workflow import require_decision


def _organization(employer):
    employer = (employer or '').strip()
    if not employer:
        frappe.throw('Organization is required')
    name = employer if frappe.db.exists('Job Search Employer', employer) else frappe.db.exists(
        'Job Search Employer', {'organization_name': employer})
    if name:
        return require_doc('Job Search Employer', name, 'read')
    return frappe.get_doc({'doctype':'Job Search Employer',
                           'organization_name': employer}).insert()


def register_opportunity(*, employer, name=None):
    """Create a hiring pursuit, independent of Job Search membership."""
    require_operator()
    org = _organization(employer)
    opportunity_name = (name or org.organization_name or '').strip()
    if not opportunity_name:
        frappe.throw('Opportunity name is required')
    existing = frappe.get_all('Opportunity',filters={'organization':org.name},
                              fields=['name','opportunity_name'],limit_page_length=1000)
    same = next((x for x in existing if x.opportunity_name.casefold()==opportunity_name.casefold()),None)
    if same:
        return {'opportunity':same.name,'organization':org.name,'created':False}
    doc = frappe.get_doc({'doctype':'Opportunity','organization':org.name,
                          'opportunity_name':opportunity_name,'status':'Discovered',
                          'discovered_on':nowdate()}).insert()
    return {'opportunity':doc.name,'organization':org.name,'created':True}


def register_job(*, employer, title, source_url=None, description=None,
                 requisition_id=None, location=None,source_name='Employer website',
                 opportunity=None):
    """Record a Job once, then attach it to an existing/default Opportunity."""
    require_operator()
    org=_organization(employer)
    title=(title or '').strip()
    if not title or not (source_url or description):
        frappe.throw('Job title and a source URL or description are required')
    found=None
    if source_url:
        found=frappe.db.get_value('Job Search Posting',{'source_url':source_url},'job')
        found=found or frappe.db.get_value('Job Search Source',{'url':source_url},'job')
    candidates=frappe.get_all('Job',filters={'organization':org.name},
                              fields=['name','job_title','requisition_id','location'],
                              limit_page_length=100000)
    if not found and requisition_id:
        matches=[x.name for x in candidates if x.requisition_id==requisition_id and
                 (x.job_title or '').casefold()==title.casefold() and
                 (x.location or '').casefold()==(location or '').casefold()]
        if len(matches)==1:
            found=matches[0]
    if found:
        role=require_doc('Job',found,'write')
        if role.organization != org.name:
            frappe.throw('Existing Job belongs to another Organization')
        created=False
    else:
        role=frappe.get_doc({'doctype':'Job','organization':org.name,
                             'job_title':title,'requisition_id':requisition_id,
                             'posting_url':source_url,'location':location,
                             'discovered_on':nowdate(),'availability_status':'Unknown',
                             'compensation_not_given':1}).insert()
        created=True
    from job_search.opportunities import associate_job, opportunities_for_job
    linked=opportunities_for_job(role.name)
    if opportunity:
        target=require_doc('Opportunity',opportunity,'write')
        if target.organization != org.name:
            frappe.throw('Opportunity belongs to another Organization')
    elif linked:
        if len(linked)>1:
            frappe.throw('Job belongs to multiple Opportunities; select one explicitly')
        opportunity=linked[0]
    else:
        existing=frappe.get_all('Opportunity',filters={'organization':org.name},pluck='name',
                                limit_page_length=1000)
        if len(existing)>1:
            frappe.throw('Multiple Opportunities exist for this Organization; select one')
        if existing:
            opportunity=existing[0]
        else:
            opportunity=register_opportunity(employer=org.name)['opportunity']
    associate_job(opportunity,role.name)
    snapshot=None
    if description:
        snapshot=capture_posting(role.name,description=description,source_name=source_name,
                                 source_url=source_url,posting_title=title,
                                 requisition_id=requisition_id,opportunity=opportunity)
    elif source_url and not frappe.db.exists('Job Search Source',{'url':source_url,'job':role.name}):
        frappe.get_doc({'doctype':'Job Search Source','title':f'{title} (discovery)',
            'url':source_url,'source_type':'Job Board','retrieved_on':now_datetime(),
            'job':role.name,'opportunity':opportunity,'organization':org.name,
            'verification_status':'Unverified'}).insert()
    return {'job':role.name,'opportunity':opportunity,'organization':org.name,
            'created':created,'posting':snapshot['posting'] if snapshot else None,
            'snapshot_created':snapshot['created'] if snapshot else False,
            'possible_duplicates':[x.name for x in candidates if x.name!=role.name and
                                   (x.job_title or '').casefold()==title.casefold()]}


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
    deal.latest_application = application.name
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
    deal.interview_schedule = (
        f"{interview_type} — {scheduled_at or 'not scheduled'} "
        f"({timezone or 'timezone not set'})"
    )
    deal.save()
    return doc.name
