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
    migrate_legacy_search_filters()
    ensure_workspace()
    ensure_app_logo()
    frappe.clear_cache()
    # Frappe's merged language dictionary has its own cache, independent of
    # the Desk/doctype caches. Refresh it when app translations change.
    from frappe.translate import clear_cache as clear_translation_cache

    clear_translation_cache()


WORKSPACE_LABELS = {
    'Job Search Search': 'Searches',
    'Job Search Opportunity': 'Jobs',
    'Job Search Employer': 'Organizations',
    'Job Search Task': 'Tasks',
    'Job Search Posting': 'Postings',
    'Job Search Research': 'Research',
    'Job Search Decision': 'Decisions',
    'Job Search Application': 'Applications',
    'Job Search Interview': 'Interviews',
    'Job Search Procedure Execution': 'Procedure Runs',
    'Job Search Procedure': 'Procedures',
    'Job Search Source': 'Sources',
    'Job Search Transition': 'Stage History',
}


def ensure_workspace():
    """Keep display labels friendly while retaining stable underlying DocTypes."""
    names = (
        "Job Search Search", "Job Search Opportunity", "Job Search Employer", "Job Search Task",
        "Job Search Posting", "Job Search Research", "Job Search Decision",
        "Job Search Application", "Job Search Interview", "Job Search Procedure Execution",
    )
    links = [{"type": "DocType", "link_to": name,
              "label": WORKSPACE_LABELS[name], "doc_view": "List"} for name in names]
    content = ([{"type": "header", "data": {"text": "Job Search", "col": 12}}]
               + [{"type": "shortcut", "data": {"shortcut_name": WORKSPACE_LABELS[name], "col": 4}}
                  for name in names])
    if frappe.db.exists("Workspace", "Job Search"):
        doc = frappe.get_doc("Workspace", "Job Search")
        by_doctype = {row.link_to: row for row in doc.shortcuts if row.type == "DocType"}
        for item in links:
            if item["link_to"] in by_doctype:
                by_doctype[item["link_to"]].label = item["label"]
            else:
                doc.append("shortcuts", item)
        old_to_new = {name: WORKSPACE_LABELS[name] for name in names}
        current = frappe.parse_json(doc.content or "[]")
        seen = set()
        for item in current:
            shortcut = item.get("data", {}).get("shortcut_name")
            if shortcut in old_to_new:
                item["data"]["shortcut_name"] = old_to_new[shortcut]
                shortcut = item["data"]["shortcut_name"]
            if shortcut:
                seen.add(shortcut)
        for item in content:
            shortcut = item.get("data", {}).get("shortcut_name")
            if shortcut and shortcut not in seen:
                current.append(item)
        doc.content = json.dumps(current)
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


def migrate_legacy_search_filters():
    """Move old search filters after schema sync, then clear legacy values.

    Frappe executes patches before DocType sync, so a schema-changing patch
    cannot reliably copy a newly added column. Clearing old values prevents
    subsequent migrations from restoring a filter intentionally cleared by a user.
    """
    columns = set(frappe.db.get_table_columns("Job Search Search"))
    for old, new in (("title_contains", "title_matches"),
                     ("location_contains", "location_match")):
        if {old, new}.issubset(columns):
            frappe.db.sql(
                f"UPDATE `tabJob Search Search` SET `{new}` = `{old}` "
                f"WHERE COALESCE(`{new}`, '') = '' AND COALESCE(`{old}`, '') != ''"
            )
            frappe.db.sql(
                f"UPDATE `tabJob Search Search` SET `{old}` = NULL "
                f"WHERE `{old}` IS NOT NULL AND `{old}` != ''"
            )
