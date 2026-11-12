"""Rename the existing job-like Opportunity DocType to Job without losing identifiers.

The actual Opportunity records and their supporting Job links are created
*after* DocType sync by setup.migrate_opportunities_v5. Renaming before sync
allows Frappe to update existing metadata and generic Link references safely.
"""

import frappe
from frappe.model.rename_doc import rename_doc


def execute():
    previous = frappe.session.user
    frappe.set_user("chatgpt.a01.2428478@gmail.com")
    try:
        old, new = "Job Search Opportunity", "Job"
        if frappe.db.exists("DocType", old):
            if frappe.db.exists("DocType", new):
                frappe.throw("Cannot split Opportunities: destination Job already exists")
            rename_doc("DocType", old, new, force=True, ignore_permissions=True,
                       validate=False, show_alert=False, rebuild_search=False)
    finally:
        frappe.set_user(previous)
