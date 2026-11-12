"""Idempotent issue #25 update of the official Frappe Research Handbook."""

import frappe

ASSISTANT = 'chatgpt.a01.2428478@gmail.com'
ROUTE = 'docs/research-handbook/start-here'
OLD = (
    'Opportunity owns research workflow, decisions, Activity Log, applications, '
    'interviews, offers, tasks, and scoped rejection.'
)
NEW = (
    OLD
    + ' The read-only **Applied** checkbox on Opportunity is derived entirely from '
    'the Activity Log: it is true if at least one row has Type **Application**, '
    'otherwise false, regardless of the pursuit Status. It is searchable, '
    'filterable, and updates automatically when activities are added, edited, '
    'or removed; never set it manually.'
)


def update():
    if frappe.session.user != ASSISTANT:
        frappe.throw('Dedicated assistant account required for handbook update')
    doc = frappe.get_doc('Wiki Document', {'route': ROUTE})
    if doc.owner != ASSISTANT:
        frappe.throw('Unexpected handbook owner')
    content = doc.content or ''
    if NEW in content:
        return {'updated': False, 'route': ROUTE}
    if content.count(OLD) != 1:
        frappe.throw('Unexpected handbook text; refusing an unreviewed update')
    doc.content = content.replace(OLD, NEW)
    doc.save()
    return {'updated': True, 'route': ROUTE}
