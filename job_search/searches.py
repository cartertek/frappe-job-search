"""Independent job collections, declarative search matching and explicit overrides."""

import frappe
from frappe.utils import getdate

from job_search.permissions import require_doc, require_operator

JOB = 'Job Search Opportunity'
EMPLOYER = 'Job Search Employer'
SEARCH = 'Job Search Search'


def matches(job, search):
    """Pure deterministic predicate; subjective heuristics are never executed."""
    for candidate, pattern in (
        (job.js_job_title, search.title_contains),
        (job.js_location, search.location_contains),
    ):
        if pattern and pattern.casefold() not in (candidate or '').casefold():
            return False
    for job_value, needed in (
        (job.js_employment_type, search.employment_type),
        (job.js_work_arrangement, search.work_arrangement),
        (job.js_seniority, search.seniority),
    ):
        if needed and (job_value or '').casefold() != needed.casefold():
            return False
    if search.posted_after and (
        not job.js_posted_on or getdate(job.js_posted_on) < getdate(search.posted_after)
    ):
        return False
    if search.compensation_period and job.js_compensation_period != search.compensation_period:
        return False
    if search.salary_min:
        if search.currency and job.js_currency != search.currency:
            return False
        # Unknown salary doesn't satisfy a minimum; don't silently assume it does.
        if not job.js_compensation_min or float(job.js_compensation_min) < float(search.salary_min):
            return False
    return True


def matching_jobs(search_name):
    require_operator()
    search = require_doc(SEARCH, search_name)
    # Avoid leaking any jobs not readable to this user through membership records.
    jobs = frappe.get_list(JOB, fields=[
        'name', 'organization', 'js_job_title', 'js_location', 'js_employment_type',
        'js_work_arrangement', 'js_seniority', 'js_posted_on', 'js_compensation_min',
        'js_currency', 'js_compensation_period', 'globally_rejected', 'js_stage',
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
