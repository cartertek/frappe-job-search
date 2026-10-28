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
    migrate_prefixed_fields()
    migrate_workflow_statuses()
    migrate_legacy_search_filters()
    migrate_heuristics_table()
    ensure_workspace()
    ensure_app_logo()
    frappe.clear_cache()
    # Frappe 16 caches Desk FormMeta separately in frappe.client_cache. A normal
    # site cache clear does not invalidate that cached bundle, so a newly added
    # native child-grid template can remain absent from browser metadata.
    frappe.cache.delete_value("doctype_form_meta::Job Search Search")
    # Frappe's merged language dictionary has its own cache, independent of
    # the Desk/doctype caches. Refresh it when app translations change.
    from frappe.translate import clear_cache as clear_translation_cache

    clear_translation_cache()


WORKSPACE_LABELS = {
    'Job Search Search': 'Search',
    'Job Search Opportunity': 'Job',
    'Job Search Employer': 'Organization',
    'Job Search Task': 'Task',
    'Job Search Posting': 'Posting',
    'Job Search Research': 'Research',
    'Job Search Decision': 'Decision',
    'Job Search Application': 'Application',
    'Job Search Interview': 'Interview',
    'Job Search Procedure Execution': 'Procedure Run',
    'Job Search Procedure': 'Procedure',
    'Job Search Source': 'Source',
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
        legacy_plural = {
            "Searches": "Search", "Jobs": "Job", "Organizations": "Organization",
            "Tasks": "Task", "Postings": "Posting", "Decisions": "Decision",
            "Applications": "Application", "Interviews": "Interview",
            "Procedure Runs": "Procedure Run",
        }
        old_to_new = {name: WORKSPACE_LABELS[name] for name in names}
        old_to_new.update(legacy_plural)
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


def migrate_prefixed_fields():
    """Copy historical js_-prefixed columns to their unprefixed replacements.

    Do not delete legacy columns: this is idempotent, preserving rollback data.
    Re-runs only copy into NULL replacement cells. A dedicated migration marker
    prevents reinstating values that users later deliberately clear.
    """
    mapping = {
        'Job Search Opportunity': {
            'js_job_title': 'job_title',
            'js_posting_url': 'posting_url',
            'js_requisition_id': 'requisition_id',
            'js_employment_type': 'employment_type',
            'js_work_arrangement': 'work_arrangement',
            'js_location': 'location',
            'js_compensation_min': 'compensation_min',
            'js_compensation_max': 'compensation_max',
            'js_currency': 'currency',
            'js_compensation_period': 'compensation_period',
            'js_seniority': 'seniority',
            'js_discovered_on': 'discovered_on',
            'js_posted_on': 'posted_on',
            'js_deadline': 'deadline',
            'js_qualification': 'qualification',
            'js_qualification_rationale': 'qualification_rationale',
            'js_applied_on': 'applied_on',
            'js_next_action_on': 'next_action_on',
            'js_priority': 'priority',
            'js_stage': 'status',
            'js_closure_reason': 'closure_reason',
            'js_offer_details': 'offer_details',
            'js_posting_digest': 'posting_digest',
            'js_research_digest': 'research_digest',
            'js_agent_recommendation': 'agent_recommendation',
            'js_application_review': 'application_review',
            'js_interview_brief': 'interview_brief',
            'js_human_feedback': 'human_feedback',
            'js_human_action': 'human_action',
            'js_human_action_rationale': 'human_action_rationale',
            'js_review_request': 'review_request',
            'js_review_status': 'review_status',
            'js_review_assigned_to': 'review_assigned_to',
            'js_review_task': 'review_task',
            'js_posting_text': 'posting_text',
            'js_latest_posting': 'latest_posting',
            'js_last_decision': 'last_decision',
            'js_last_decision_record': 'last_decision_record',
            'js_latest_application': 'latest_application',
            'js_interview_schedule': 'interview_schedule',
            'js_review_assignment': 'review_assignment',
        },
        'Job Search Employer': {
            'js_careers_url': 'careers_url',
            'js_employer_category': 'employer_category',
            'js_employer_priority': 'employer_priority',
            'js_research_status': 'research_status',
            'js_last_researched': 'last_researched',
            'js_employment_notes': 'employment_notes',
        },
        'Job Search Task': {
            'js_priority': 'priority',
            'js_stage': 'status',
            'js_transition': 'transition',
        },
    }
    marker = "job_search:prefixed_fields_copied_v1"
    if frappe.db.get_default(marker):
        return
    for doctype, replacements in mapping.items():
        columns = set(frappe.db.get_table_columns(doctype))
        for previous, current in replacements.items():
            if {previous, current}.issubset(columns):
                if previous == "js_stage" and current == "status":
                    # The old duplicate status holds values like "JS: Discovered".
                    # Always replace it with the authoritative previous stage.
                    frappe.db.sql(
                        f"UPDATE `tab{doctype}` SET `status` = `js_stage` "
                        "WHERE `js_stage` IS NOT NULL"
                    )
                else:
                    frappe.db.sql(
                        f"UPDATE `tab{doctype}` SET `{current}` = `{previous}` "
                        f"WHERE `{current}` IS NULL AND `{previous}` IS NOT NULL"
                    )
    frappe.db.set_default(marker, "1")


def migrate_workflow_statuses():
    """Collapse removed workflow stages after DocType sync, preserving history."""
    marker = "job_search:workflow_v2_statuses"
    if frappe.db.get_default(marker):
        return
    mapping = {
        "Preparing": "Qualified",
        "Screening": "Applied",
        "Offer": "Interviewing",
        "Withdrawn": "Rejected",
        "Closed": "Rejected",
    }
    for old, new in mapping.items():
        frappe.db.sql(
            "UPDATE `tabJob Search Opportunity` SET status=%s WHERE status=%s", (new, old)
        )
    frappe.db.set_default(marker, "1")


def migrate_heuristics_table():
    """Preserve old free-text instructions as a named heuristic child row.

    The old SQL column is kept for rollback. The migration is idempotent and
    never overwrites manually edited child rows.
    """
    if "heuristics" not in frappe.db.get_table_columns("Job Search Search"):
        return
    if not frappe.db.exists("DocType", "Job Search Heuristic"):
        return
    existing = frappe.db.sql(
        "SELECT name, heuristics FROM `tabJob Search Search` "
        "WHERE COALESCE(heuristics, '') != ''", as_dict=True
    )
    for record in existing:
        if frappe.db.exists("Job Search Heuristic", {
            "parent": record.name, "parenttype": "Job Search Search",
            "parentfield": "heuristics",
        }):
            continue
        doc = frappe.get_doc("Job Search Search", record.name)
        doc.append("heuristics", {
            "heuristic_name": "Existing Research Heuristics",
            "description": record.heuristics,
        })
        doc.save(ignore_permissions=True)
