"""Idempotent reconciliation of official Research Handbook with the current model.

Run only on the Frappe site as the dedicated assistant operator. Never change
owner or modified_by metadata, and refuse unexpected source text.
"""

import frappe

ASSISTANT = 'chatgpt.a01.2428478@gmail.com'

REPLACEMENTS = {
    'docs/research-handbook/opportunity-research': [
        (
            'Subsequent Applied / Interviewing / Accepted stages require respectively '
            'an authorized saved Opportunity application, an Opportunity interview, '
            'and offer details plus human Accept Offer authorization.',
            'Subsequent Applied / Interviewing / Accepted stages require respectively '
            'a signed-in human approver and an Application Activity Log row (not a '
            'separate Authorize Application decision or detailed submission record), '
            'an Interview Activity Log row and Opportunity interview record, and an '
            'Acceptation Activity Log row with offer details plus the actual human '
            'Accept Offer decision.',
        ),
    ],
    'docs/research-handbook/qualification-and-prioritization': [
        ('## From research to Job status', '## From research to Opportunity status'),
    ],
    'docs/research-handbook/start-here': [
        (
            'Opportunity owns research workflow, decisions, applications, '
            'interviews, offers, tasks, and scoped rejection.',
            'Opportunity owns research workflow, decisions, Activity Log, '
            'applications, interviews, offers, tasks, and scoped rejection. '
            'Activity Log entries are ordered by Date ascending; manually added '
            'entries require an explicit Type. Only Opportunity Globally and Entire '
            'Organization rejections create a Rejection activity (dated today with '
            'the reason in Notes) if none exists; Search Only and individual Job '
            'rejections do not.',
        ),
    ],
}


def update():
    if frappe.session.user != ASSISTANT:
        frappe.throw('The Research Handbook may only be edited as the dedicated assistant account')
    changed = []
    # Validate every page first, so a partial edit is not accidentally committed.
    pages = []
    for route, pairs in REPLACEMENTS.items():
        doc = frappe.get_doc('Wiki Document', {'route': route})
        if doc.owner != ASSISTANT:
            frappe.throw(f'Unexpected Wiki owner for {route}')
        text = doc.content or ''
        for old, new in pairs:
            if old not in text and new not in text:
                frappe.throw(f'Expected text missing in {route}: {old[:100]}')
            if text.count(old) > 1:
                frappe.throw(f'Ambiguous source text in {route}: {old[:100]}')
            if old != new:
                text = text.replace(old, new)
        pages.append((doc, text))
    for doc, revised in pages:
        if (doc.content or '') != revised:
            doc.content = revised
            doc.save()
            changed.append(doc.route)
    return {'reviewed': len(pages), 'updated': changed}
