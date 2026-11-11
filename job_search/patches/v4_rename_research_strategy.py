"""Rename strategy DocTypes in place; retain document IDs, assignments and links."""

import frappe
from frappe.model.rename_doc import rename_doc


def execute():
    # Patches run before new DocType JSON is synchronized. Frappe handles
    # physical table renames, Link targets and child table parenttypes.
    previous_actor = frappe.session.user
    frappe.set_user("chatgpt.a01.2428478@gmail.com")
    try:
        for old, new in (
            ("Job Search Research Strategy", "Research Strategy"),
            ("Job Search Assigned Research Strategy", "Assigned Research Strategy"),
        ):
            if not frappe.db.exists("DocType", old):
                continue
            if frappe.db.exists("DocType", new):
                frappe.throw(f"Cannot rename {old}: destination {new} already exists")
            # This is a controlled schema migration. Do not impersonate the user
            # or Administrator; attribute it to our assistant account.
            rename_doc("DocType", old, new, force=True,
                       ignore_permissions=True, validate=False, show_alert=False,
                       rebuild_search=False)
    finally:
        frappe.set_user(previous_actor)
