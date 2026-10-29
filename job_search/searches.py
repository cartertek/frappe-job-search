"""Independent job collections, declarative search matching and explicit overrides."""

import frappe
from frappe.utils import getdate

from job_search.permissions import require_doc, require_operator

JOB = 'Job Search Opportunity'
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
    if search.posted_after and (not job.posted_on or getdate(job.posted_on) < getdate(search.posted_after)):
        failures.append(
            f"Posted On: {job.posted_on or '(missing)'}; required on or after {search.posted_after}"
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
            if job.compensation_min is not None and float(job.compensation_min) < float(search.salary_min):
                failures.append(
                    f"Minimum Compensation: {job.compensation_min}; required at least {search.salary_min}"
                )
    return failures


def matches(job, search):
    """Pure deterministic predicate; subjective heuristics are never executed."""
    return not match_failures(job, search)


def matching_jobs(search_name):
    require_operator()
    search = require_doc(SEARCH, search_name)
    # Avoid leaking any jobs not readable to this user through membership records.
    jobs = frappe.get_list(JOB, fields=[
        'name', 'organization', 'job_title', 'location', 'employment_type',
        'work_arrangement', 'seniority', 'posted_on', 'compensation_min',
        'currency', 'compensation_period', 'compensation_not_given', 'globally_rejected', 'status',
    ], limit_page_length=100000)
    employers = {j.organization for j in jobs if j.organization}
    rejected = set()
    for org in employers:
        if frappe.db.get_value(EMPLOYER, org, 'globally_rejected'):
            rejected.add(org)
    overrides = {r.job: r.override for r in search.overrides}
    results = []
    for job in jobs:
        if job.globally_rejected or job.organization in rejected:
            continue  # Global rejection always wins, including explicit Include.
        override = overrides.get(job.name)
        if override == 'Exclude':
            continue
        if override == 'Include' or (not search.require_heuristics and matches(job, search)):
            results.append({
                **dict(job),
                'match_reason': 'Explicit Include' if override == 'Include' else 'Filters',
            })
    return results


def set_membership(search_name, job_name, override):
    require_operator()
    search = require_doc(SEARCH, search_name, 'write')
    require_doc(JOB, job_name, 'read')
    if override not in ('Include', 'Exclude', 'Default'):
        frappe.throw('Override must be Include, Exclude or Default')
    existing = [r for r in search.overrides if r.job == job_name]
    for row in existing:
        search.remove(row)
    if override != 'Default':
        search.append('overrides', {'job': job_name, 'override': override})
    search.save()
    return {'search': search_name, 'job': job_name, 'override': override}


def reject_job(job_name):
    require_operator()
    job = require_doc(JOB, job_name, 'write')
    job.globally_rejected = 1
    job.save()
    return job.name


def reject_employer(employer_name):
    require_operator()
    employer = require_doc(EMPLOYER, employer_name, 'write')
    employer.globally_rejected = 1
    employer.save()
    return employer.name
