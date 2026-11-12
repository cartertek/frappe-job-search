"""Relationships and eligibility of organization-level hiring opportunities."""

import frappe

from job_search.permissions import require_doc, require_operator


def opportunities_for_job(job):
    return frappe.get_all('Opportunity Job', filters={'job': job}, pluck='parent',
                          limit_page_length=100000)


def jobs_for_opportunity(opportunity):
    return frappe.get_all('Opportunity Job', filters={'parent': opportunity,
                          'parenttype': 'Opportunity'}, pluck='job', limit_page_length=100000)


def recheck_for_job(doc, method=None):
    """Reassess all associated Opportunities when a Job's evidence changes.

    A completed historical pursuit is not erased. Ready to Review is withdrawn
    when no Job qualifies, while later stages retain their history and expose
    Current Eligibility = Needs Research for operator action.
    """
    from job_search.workflow import _review_readiness_failures

    for name in opportunities_for_job(doc.name):
        opportunity = frappe.get_doc('Opportunity', name)
        if not opportunity.active_job_search:
            continue
        eligible = not _review_readiness_failures(opportunity)
        desired = 'Eligible' if eligible else 'Needs Research'
        if opportunity.eligibility_status == desired and (eligible or opportunity.status != 'Ready to Review'):
            continue
        if not eligible and opportunity.status == 'Ready to Review':
            opportunity.status = 'Researching'
        opportunity.eligibility_status = desired
        opportunity.save(ignore_permissions=True)


def reject_job(job, reason):
    require_operator()
    doc = require_doc('Job', job, 'write')
    if not (reason or '').strip():
        frappe.throw('Job rejection reason is required')
    doc.availability_status = 'Rejected'
    doc.job_rejection_reason = reason.strip()
    doc.save()
    doc.add_comment('Comment', f'Job rejected independently: {reason.strip()}')
    return {'job': doc.name, 'availability_status': doc.availability_status}


def reopen_job(job, reason):
    require_operator()
    doc = require_doc('Job', job, 'write')
    if doc.availability_status != 'Rejected':
        frappe.throw('Only rejected Jobs may be reopened')
    if not (reason or '').strip():
        frappe.throw('Job reopening reason is required')
    doc.availability_status = 'Unknown'  # Do not invent proof of current activity.
    doc.save()
    doc.add_comment('Comment', f'Job reopened for availability verification: {reason.strip()}')
    return {'job': doc.name, 'availability_status': doc.availability_status}


def associate_job(opportunity, job):
    require_operator()
    opp = require_doc('Opportunity', opportunity, 'write')
    linked = require_doc('Job', job, 'read')
    if linked.organization != opp.organization:
        frappe.throw('Job and Opportunity must belong to the same Organization')
    if job not in {r.job for r in opp.jobs}:
        opp.append('jobs', {'job': job})
        opp.save()
    return {'opportunity': opportunity, 'job': job}


def reopen_organization(organization, reason):
    require_operator()
    org=require_doc('Job Search Employer',organization,'write')
    if not (reason or '').strip():
        frappe.throw('Organization reopening reason is required')
    if not org.globally_rejected:
        frappe.throw('Organization is not globally rejected')
    org.globally_rejected=0
    org.save()
    org.add_comment('Comment',f'Organization reopened: {reason.strip()}')
    return {'organization':org.name,'globally_rejected':0}
