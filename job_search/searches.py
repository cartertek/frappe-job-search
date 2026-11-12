"""Independent job collections, declarative search matching and explicit overrides."""

import frappe

from job_search.permissions import require_doc, require_operator
from job_search.recency import active_window_start, date_in_window

JOB = 'Job'
EMPLOYER = 'Job Search Employer'
SEARCH = 'Job Search Search'


def match_failures(job, search):
    """Explain each failed deterministic search criterion using the same rules as matches()."""
    failures = []
    if (
        search.location_match
        and (job.location or "").strip().casefold() != search.location_match.strip().casefold()
    ):
        failures.append(f"Location: {job.location or '(missing)'}; required: {search.location_match}")
    for label, job_value, needed in (
        ("Employment Type", job.employment_type, search.employment_type),
        ("Work Arrangement", job.work_arrangement, search.work_arrangement),
        ("Seniority", job.seniority, search.seniority),
    ):
        if needed and (job_value or "").casefold() != needed.casefold():
            failures.append(f"{label}: {job_value or '(missing)'}; required: {needed}")
    activity_start = active_window_start(search.active_in_past_count, search.active_in_past_unit)
    if not date_in_window(job.last_active_on, activity_start):
        failures.append(
            f"Last Active Date: {job.last_active_on or '(missing)'}; "
            f"required within the past {search.active_in_past_count} {search.active_in_past_unit}"
        )
    if not getattr(job, "compensation_not_given", False):
        if search.compensation_period and job.compensation_period != search.compensation_period:
            failures.append(
                f"Compensation Period: {job.compensation_period or '(missing)'};"
                f" required: {search.compensation_period}"
            )
        if search.salary_min:
            if search.currency and job.currency != search.currency:
                failures.append(f"Currency: {job.currency or '(missing)'}; required: {search.currency}")
            ceiling = (
                job.compensation_max if getattr(job, "compensation_max", None) is not None
                else job.compensation_min
            )
            if ceiling is not None and float(ceiling) < float(search.salary_min):
                failures.append(
                    f"Advertised Compensation Maximum: {ceiling}; required at least {search.salary_min}"
                )
    return failures


def matches(job, search):
    """Pure deterministic predicate; subjective heuristics are never executed."""
    return not match_failures(job, search)


def matching_jobs(search_name):
    """Job-level deterministic matches, with Opportunity-level override/rejection."""
    require_operator()
    search = require_doc(SEARCH, search_name)
    jobs = frappe.get_list('Job', fields=[
        'name','organization','job_title','location','employment_type',
        'work_arrangement','seniority','last_active_on','compensation_min',
        'compensation_max','currency','compensation_period','compensation_not_given',
        'availability_status'],limit_page_length=100000)
    by_job = {}
    for row in frappe.get_all('Opportunity Job', fields=['parent','job'],limit_page_length=100000):
        by_job.setdefault(row.job, []).append(row.parent)
    overrides = {r.opportunity: r.override for r in search.overrides}
    permitted = {o.name:o for o in frappe.get_list('Opportunity',fields=[
        'name','organization','opportunity_name','status','globally_rejected'],limit_page_length=100000)}
    rejected_orgs = {name for name in {o.organization for o in permitted.values()} if
                     frappe.db.get_value(EMPLOYER,name,'globally_rejected')}
    found = {}
    for job in jobs:
        if job.availability_status in ('Closed','Rejected') or job.organization in rejected_orgs:
            continue
        deterministic = matches(job,search)
        for name in by_job.get(job.name,[]):
            opp = permitted.get(name)
            if not opp or opp.globally_rejected or opp.organization != job.organization:
                continue
            override = overrides.get(name)
            if override == 'Exclude':
                continue
            if override != 'Include' and (search.require_heuristics or not deterministic):
                continue
            result = found.setdefault(name,{'opportunity':name,'organization':opp.organization,
                'opportunity_name':opp.opportunity_name,
                'organization_name':frappe.db.get_value(EMPLOYER,opp.organization,'organization_name'),
                'status':opp.status,'qualifying_jobs':[],'qualifying_job_labels':[],
                'match_reason':'Explicit Include' if override=='Include' else 'Filters'})
            result['qualifying_jobs'].append(job.name)
            title=(job.job_title or job.name)
            result['qualifying_job_labels'].append(
                f'{title} ({job.name})' if title != job.name else job.name
            )
    return list(found.values())


def set_membership(search_name, opportunity_name, override):
    require_operator()
    search = require_doc(SEARCH,search_name,'write')
    require_doc('Opportunity',opportunity_name,'read')
    if override not in ('Include','Exclude','Default'):
        frappe.throw('Override must be Include, Exclude or Default')
    for row in list(search.overrides):
        if row.opportunity == opportunity_name:
            search.remove(row)
    if override != 'Default':
        search.append('overrides',{'opportunity':opportunity_name,'override':override})
    search.save()
    return {'search':search_name,'opportunity':opportunity_name,'override':override}


def reject_employer(employer_name, reason):
    require_operator()
    employer=require_doc(EMPLOYER,employer_name,'write')
    if not (reason or '').strip():
        frappe.throw('Organization rejection reason required')
    if not employer.globally_rejected:
        employer.globally_rejected=1
        employer.save()
    employer.add_comment('Comment',f'Organization rejected globally: {reason.strip()}')
    return employer.name
