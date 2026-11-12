"""Immutable, job-specific publication snapshots; record full original text."""

import hashlib

import frappe
from frappe.utils import now_datetime, nowdate

from job_search.permissions import require_doc, require_operator
from job_search.opportunities import opportunities_for_job


def content_hash(description):
    return hashlib.sha256((description or '').encode('utf-8')).hexdigest()


def capture_posting(job, *, description, source_name, source_url=None,
                    posting_title=None, requisition_id=None, snapshot=None,
                    opportunity=None):
    require_operator()
    role = require_doc('Job', job, 'write')
    if not (description or '').strip() or not (source_name or '').strip():
        frappe.throw('A full posting description and source name are required')
    related = opportunities_for_job(role.name)
    if opportunity and opportunity not in related:
        frappe.throw('The selected Opportunity is not associated with the Job')
    if not opportunity and len(related) == 1:
        opportunity = related[0]
    if not opportunity and len(related) > 1:
        frappe.throw('Specify which Opportunity this posting supports')
    filters = {'job': role.name, 'source_name': source_name,
               'source_url': source_url if source_url else ['is', 'not set']}
    latest = frappe.db.get_value('Job Search Posting', filters,
                                 ['name','content_hash'],order_by='creation desc',as_dict=True)
    digest = content_hash(description)
    if latest and latest.content_hash == digest:
        if role.latest_posting != latest.name:
            role.latest_posting=latest.name
            role.save()
        return {'posting':latest.name,'created':False}
    entry = frappe.get_doc({'doctype':'Job Search Posting', 'job':role.name,
        'opportunity':opportunity,'organization':role.organization,
        'source_name':source_name,'source_url':source_url,
        'posting_title':posting_title or role.job_title,
        'requisition_id':requisition_id or role.requisition_id,
        'description':description,'snapshot':snapshot,
        'supersedes':latest.name if latest else None,'retrieved_on':now_datetime(),
        'first_observed':nowdate(),'last_observed':nowdate(),
        'content_hash':digest,'status':'Unknown'}).insert()
    role.latest_posting=entry.name
    role.job_description=description
    role.save()
    return {'posting':entry.name,'created':True,'supersedes':latest.name if latest else None}
