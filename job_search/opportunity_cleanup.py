"""Idempotent correction of the first Opportunity/Job split (issue #15).

The initial migration conservatively kept one Opportunity per historical Job.
This correction consolidates only Organizations with identical, compatible
pursuit histories, after taking a complete in-database archival snapshot.
Distinct hiring teams or conflicting approval histories fail closed.
"""

from collections import defaultdict

import frappe

ASSISTANT = 'chatgpt.a01.2428478@gmail.com'
MARKER = 'job_search:opportunity_cleanup_v6'
REFERENCE_DOCTYPES = (
    'Job Search Task', 'Job Search Decision', 'Job Search Transition',
    'Job Search Application', 'Job Search Interview', 'Job Search Research',
    'Job Search Source', 'Job Search Posting', 'Job Search Procedure Execution',
)
RICH_FIELDS = (
    'research_findings', 'research_recommendation',
    'application_materials_for_review', 'interview_preparation',
    'human_feedback_and_instructions',
)


def _related(doctype, name, field='opportunity'):
    return frappe.get_all(doctype, filters={field: name}, fields=['*'],
                          limit_page_length=100000)


def _archive(original, target):
    if frappe.db.exists('Opportunity Consolidation', {'old_opportunity': original.name}):
        return
    linked = {dt: _related(dt, original.name) for dt in REFERENCE_DOCTYPES}
    linked['Job Search Membership'] = _related('Job Search Membership', original.name)
    for dt, fields in (
        ('Comment', {'reference_doctype': 'Opportunity', 'reference_name': original.name}),
        ('Version', {'ref_doctype': 'Opportunity', 'docname': original.name}),
        ('ToDo', {'reference_type': 'Opportunity', 'reference_name': original.name}),
        ('Tag Link', {'document_type': 'Opportunity', 'document_name': original.name}),
    ):
        linked[dt] = frappe.get_all(dt, filters=fields, fields=['*'], limit_page_length=100000)
    frappe.get_doc({
        'doctype': 'Opportunity Consolidation',
        'old_opportunity': original.name,
        'canonical_opportunity': target.name,
        'original_organization': original.organization,
        'source_snapshot': frappe.as_json({
            'opportunity': original.as_dict(), 'linked_records': linked,
        }),
    }).insert(ignore_permissions=True)


def _merge_text(left, right, title, old_id):
    if not right or not str(right).strip():
        return left
    if str(right).strip() == str(left or '').strip():
        return left
    heading = f'<h3>Research for {frappe.utils.escape_html(title or old_id)} ({old_id})</h3>'
    return (str(left or '') + '\n' + heading + '\n' + str(right)).strip()


def _compatible(group):
    if len(group) < 2:
        return True
    if len({d.organization for d in group}) != 1:
        return False
    # If the pursuing human has approved any distinct record, do not merge
    # under a synthetic shared stage. These require individual review.
    if any(d.status in ('Qualified', 'Applied', 'Interviewing', 'Accepted')
           or d.last_decision_record for d in group):
        return False
    scopes = {d.rejection_scope or '' for d in group}
    if scopes - {'', 'Search Only', 'Opportunity Globally', 'Entire Organization'}:
        return False
    if len({d.status for d in group}) != 1:
        return False
    if len({bool(d.globally_rejected) for d in group}) != 1:
        return False
    if len({d.active_job_search for d in group}) > 1:
        return False
    if len({d.rejection_scope or '' for d in group}) > 1:
        return False
    return True


def _merge_one(source, canonical):
    old = frappe.get_doc('Opportunity', source)
    target = frappe.get_doc('Opportunity', canonical)
    if old.organization != target.organization:
        frappe.throw('Cannot consolidate Opportunities across Organizations')
    _archive(old, target)
    job_titles = [frappe.db.get_value('Job', row.job, 'job_title') or row.job
                  for row in old.jobs]
    label = ', '.join(job_titles) or old.opportunity_name
    for field in RICH_FIELDS:
        target.set(field, _merge_text(target.get(field), old.get(field), label, source))
    if (not target.rejection_reason and old.rejection_reason):
        target.rejection_reason = old.rejection_reason
    if old.rejection_reason and old.rejection_reason != target.rejection_reason:
        target.research_findings = _merge_text(
            target.research_findings, old.rejection_reason,
            f'Rejection rationale for {label}', source,
        )
    if not target.rejection_search and old.rejection_search:
        target.rejection_search = old.rejection_search
    priority_order = {'': 0, 'Low': 1, 'Medium': 2, 'High': 3, 'Critical': 4}
    if priority_order.get(old.priority or '', 0) > priority_order.get(target.priority or '', 0):
        target.priority = old.priority
    if old.next_action_on and (not target.next_action_on or old.next_action_on < target.next_action_on):
        target.next_action_on = old.next_action_on
    if old.discovered_on and (not target.discovered_on or old.discovered_on < target.discovered_on):
        target.discovered_on = old.discovered_on
    existing_jobs = {r.job for r in target.jobs}
    for row in old.jobs:
        if row.job not in existing_jobs:
            target.append('jobs', {'job': row.job})
            existing_jobs.add(row.job)
    target.save(ignore_permissions=True)
    for dt in REFERENCE_DOCTYPES:
        frappe.db.sql(f'''UPDATE `tab{dt}` SET opportunity=%s WHERE opportunity=%s''',
                      (canonical, source))
    for row in _related('Job Search Membership', source):
        existing = frappe.db.exists('Job Search Membership',
                                     {'parent': row.parent, 'opportunity': canonical})
        if existing:
            # Search exclusions must survive; duplicate rows are archived above.
            canonical_override = frappe.db.get_value('Job Search Membership', existing, 'override')
            if row.override == 'Exclude' and canonical_override != 'Exclude':
                frappe.db.set_value('Job Search Membership', existing, 'override', 'Exclude',
                                    update_modified=False)
            frappe.db.delete('Job Search Membership', {'name': row.name})
        else:
            frappe.db.set_value('Job Search Membership', row.name, 'opportunity', canonical,
                                update_modified=False)
    # Preserve existing Job tags and propagate the union to the new Opportunity.
    for job in existing_jobs:
        for tag in frappe.get_all('Tag Link',
                 filters={'document_type': 'Job', 'document_name': job}, pluck='tag'):
            _tag(canonical, tag)
    for dt, discriminator, ref_field in (
        ('Comment', 'reference_doctype', 'reference_name'),
        ('Version', 'ref_doctype', 'docname'),
        ('ToDo', 'reference_type', 'reference_name'),
    ):
        frappe.db.sql(
            f'UPDATE `tab{dt}` SET `{ref_field}`=%s '
            f'WHERE `{ref_field}`=%s AND `{discriminator}`=%s',
            (canonical, source, 'Opportunity'),
        )
    for tag in frappe.get_all('Tag Link',
                 filters={'document_type': 'Opportunity', 'document_name': source}, pluck='tag'):
        _tag(canonical, tag)
    frappe.db.delete('Tag Link', {'document_type': 'Opportunity', 'document_name': source})
    frappe.db.delete('Opportunity Job', {'parenttype': 'Opportunity', 'parent': source})
    # Avoid deleting immutable linked documents or rewriting their authorship.
    frappe.db.delete('Opportunity', {'name': source})
    return target.name


def _tag(opportunity, tag):
    # Frappe stores tags twice: Tag Link AND the _user_tags display/search
    # column. Inserting Tag Link alone leaves tags invisible on the form.
    from frappe.desk.doctype.tag.tag import DocTags

    DocTags('Opportunity').add(opportunity, tag)


def _availability_from_postings():
    mapping = {'Active': 'Active', 'Removed': 'Closed', 'Expired': 'Closed'}
    for row in frappe.get_all('Job', fields=['name','latest_posting','availability_status'],
                              limit_page_length=100000):
        if row.availability_status not in (None, '', 'Unknown') or not row.latest_posting:
            continue
        observed = frappe.db.get_value('Job Search Posting', row.latest_posting, 'status')
        status = mapping.get(observed)
        if status:
            frappe.db.set_value('Job', row.name, 'availability_status', status,
                                update_modified=False)


def reconcile_opportunities_v6():
    """Run after DocType sync, as the dedicated operator, once per site."""
    if frappe.db.get_default(MARKER):
        return
    if not frappe.db.exists('DocType', 'Opportunity Consolidation'):
        return
    previous = frappe.session.user
    if not frappe.db.exists('User', ASSISTANT):
        frappe.throw('Dedicated assistant account is required for opportunity cleanup')
    frappe.set_user(ASSISTANT)
    try:
        groups = defaultdict(list)
        for name in frappe.get_all('Opportunity',pluck='name',limit_page_length=100000):
            doc = frappe.get_doc('Opportunity', name)
            groups[doc.organization].append(doc)
        for organization, items in groups.items():
            company_name = frappe.db.get_value('Job Search Employer', organization,
                                               'organization_name') or organization
            # Only merge historical one-Job/one-Opportunity records. A genuine
            # distinct division created after v5 must never be coalesced.
            if len(items) > 1 and any(
                not frappe.db.exists('Job', d.name) or
                d.opportunity_name != frappe.db.get_value('Job', d.name, 'job_title')
                for d in items
            ):
                frappe.throw(f'Cannot auto-merge distinct hiring efforts at {company_name}')
            if len(items) > 1 and not _compatible(items):
                frappe.throw(f'Opportunity consolidation needs review for {company_name}: '
                             'incompatible historical decisions or workflows')
            # Keep oldest historical Opportunity as canonical ID.
            items.sort(key=lambda d: (str(d.creation), d.name))
            target = items[0]
            for source in items[1:]:
                _merge_one(source.name, target.name)
            target = frappe.get_doc('Opportunity', target.name)
            if target.opportunity_name != company_name:
                target.opportunity_name = company_name
                target.save(ignore_permissions=True)
        _availability_from_postings()
        for name in frappe.get_all('Opportunity', pluck='name',limit_page_length=100000):
            for job in frappe.get_all('Opportunity Job', filters={'parent': name},pluck='job'):
                for tag in frappe.get_all('Tag Link',
                         filters={'document_type': 'Job', 'document_name': job}, pluck='tag'):
                    _tag(name, tag)
            doc = frappe.get_doc('Opportunity',name)
            doc.eligibility_status = 'Unverified' if not doc.active_job_search else 'Needs Research'
            doc.save(ignore_permissions=True)
        from job_search.opportunity_migration import verify_opportunity_migration
        verify_opportunity_migration()
        frappe.db.set_default(MARKER, '1')
    finally:
        frappe.set_user(previous)
