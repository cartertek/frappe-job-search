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
    ensure_app_logo()
    frappe.clear_cache()


def ensure_workspace():
    """Job Search lives in standard Frappe Desk; never create a parallel CRM UI."""
    names = (
        "Job Search Search", "Job Search Opportunity", "Job Search Employer", "Job Search Task",
        "Job Search Posting", "Job Search Research", "Job Search Decision",
        "Job Search Application", "Job Search Interview", "Job Search Procedure Execution",
    )
    links = [{"type": "DocType", "link_to": name, "label": name, "doc_view": "List"}
             for name in names]
    content = ([{"type": "header", "data": {"text": "Job Search", "col": 12}}]
               + [{"type": "shortcut", "data": {"shortcut_name": name, "col": 4}}
                  for name in names])
    if frappe.db.exists("Workspace", "Job Search"):
        doc = frappe.get_doc("Workspace", "Job Search")
        # Preserve user-added shortcuts while ensuring newly shipped lists appear.
        existing = {item.link_to for item in doc.shortcuts}
        for item in links:
            if item["link_to"] not in existing:
                doc.append("shortcuts", item)
        current_content = frappe.parse_json(doc.content or "[]")
        seen = {item.get("data", {}).get("shortcut_name") for item in current_content}
        for item in content:
            shortcut = item.get("data", {}).get("shortcut_name")
            if shortcut and shortcut not in seen:
                current_content.append(item)
        doc.content = json.dumps(current_content)
        doc.save(ignore_permissions=True)
    else:
        doc = frappe.get_doc({
            "doctype": "Workspace", "label": "Job Search", "title": "Job Search",
            "name": "Job Search", "module": "Job Search", "public": 1, "type": "Workspace",
            "content": json.dumps(content), "shortcuts": links,
        })
        doc.insert(ignore_permissions=True)


def ensure_app_logo():
    """Publish launcher icon in each site's shared public files for Frappe/Nginx.

    In Docker deployments the frontend and backend image asset directories can
    differ; /files is a site-shared volume exposed by the frontend.
    """
    source = Path(__file__).resolve().parents[1] / "public" / "images" / "job-search.svg"
    destination = Path(frappe.get_site_path("public", "files", "job-search.svg"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    logo = source.read_bytes()
    if not destination.exists() or destination.read_bytes() != logo:
        destination.write_bytes(logo)
