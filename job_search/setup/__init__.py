"""Install and migrate only app-owned configuration, never user research."""

import json
from pathlib import Path

import frappe


def after_install():
    after_migrate()


def after_migrate():
    """Seed app-owned immutable procedure definitions on new or migrated sites."""
    path = Path(__file__).with_name("procedures.json")
    for item in json.loads(path.read_text()):
        if frappe.db.exists("Job Search Procedure", {
            "procedure_id": item["procedure_id"], "version": item["version"],
        }):
            continue
        frappe.get_doc({"doctype": "Job Search Procedure", **item}).insert(
            ignore_permissions=True
        )
    ensure_workspace()
    frappe.clear_cache()


def ensure_workspace():
    """Job Search lives in standard Frappe Desk; never create a parallel CRM UI."""
    if frappe.db.exists("Workspace", "Job Search"):
        return
    names = (
        "Job Search Opportunity", "Job Search Employer", "Job Search Task",
        "Job Search Posting", "Job Search Research", "Job Search Decision",
        "Job Search Application", "Job Search Interview", "Job Search Procedure Execution",
    )
    links = [{"type": "DocType", "link_to": name, "label": name, "doc_view": "List"}
             for name in names]
    content = ([{"type": "header", "data": {"text": "Job Search", "col": 12}}]
               + [{"type": "shortcut", "data": {"shortcut_name": name, "col": 4}}
                  for name in names])
    doc = frappe.get_doc({
        "doctype": "Workspace", "label": "Job Search", "title": "Job Search",
        "name": "Job Search", "module": "Job Search", "public": 1, "type": "Workspace",
        "content": json.dumps(content), "shortcuts": links,
    })
    doc.insert(ignore_permissions=True)
