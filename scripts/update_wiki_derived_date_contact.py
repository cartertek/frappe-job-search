"""Idempotent official Research Handbook update for derived Activity fields."""

import frappe

ASSISTANT = 'chatgpt.a01.2428478@gmail.com'
ROUTE = 'docs/research-handbook/start-here'
SOURCE = (
    'It is searchable, filterable, and updates automatically when activities '
    'are added, edited, or removed; never set it manually.'
)
TARGET = (
    SOURCE
    + ' The read-only **Applied On** date is the most recent Date among '
    'Application activities, or blank if there are none; it can be sorted '
    'ascending or descending in the Opportunity list. **Common Contact** '
    'is the most frequent non-empty Contact across all Activity Log rows, '
    'ignoring surrounding whitespace; ties use alphabetical order. Both '
    'values are read-only, searchable, and immediately synchronized with '
    'Activity changes, including edits and deletions.'
)


def update():
    if frappe.session.user != ASSISTANT:
        frappe.throw('Dedicated assistant account required for Wiki edits')
    doc = frappe.get_doc('Wiki Document', {'route': ROUTE})
    if doc.owner != ASSISTANT:
        frappe.throw('Unexpected Wiki page owner')
    content = doc.content or ''
    if TARGET in content:
        return {'updated': False, 'route': ROUTE}
    if content.count(SOURCE) != 1:
        frappe.throw('Unexpected Wiki text; refusing unreviewed changes')
    doc.content = content.replace(SOURCE, TARGET)
    doc.save()
    return {'updated': True, 'route': ROUTE}
