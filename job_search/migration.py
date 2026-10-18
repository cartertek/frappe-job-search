"""Explicit one-time CRM -> standalone data migration.

Run after updating and migrating job_search on an image that still includes CRM.
Do NOT uninstall CRM until this verifies. Back up the site before executing.
Legacy SQL inserts are intentional: historical IDs, creators, and timestamps must
be preserved without re-running authorizations or outbound workflow hooks.
"""

import frappe

EMPLOYER_WHERE = (
    "src.name IN (SELECT DISTINCT organization FROM `tabCRM Deal` "
    "WHERE js_is_job_search = 1)"
)


def _copy(source, target, where):
    """Copy only shared columns with original primary keys, without running hooks."""
    source_columns = set(frappe.db.get_table_columns(source))
    target_columns = set(frappe.db.get_table_columns(target))
    # Source-derived workflow state remains authoritative.
    columns = sorted(source_columns & target_columns - {"js_is_job_search"})
    if "name" not in columns:
        frappe.throw(f"Historical import missing name column: {source} -> {target}")
    quoted_columns = ", ".join(f"`{column}`" for column in columns)
    select_columns = ", ".join(f"src.`{column}`" for column in columns)
    # Re-entrant: never overwrite data already imported or subsequently edited.
    return frappe.db.sql(
        f"INSERT INTO `tab{target}` ({quoted_columns}) "
        f"SELECT {select_columns} FROM `tab{source}` src WHERE {where} "
        f"AND NOT EXISTS (SELECT 1 FROM `tab{target}` dst WHERE dst.name = src.name)"
    )


def _copy_tasks():
    source, target = "CRM Task", "Job Search Task"
    common = set(frappe.db.get_table_columns(source)) & set(frappe.db.get_table_columns(target))
    cols = sorted(common - {"opportunity"})
    q = ", ".join(f"`{c}`" for c in cols + ["opportunity"])
    expr = ", ".join([f"task.`{c}`" for c in cols] + ["task.reference_docname"])
    frappe.db.sql(
        f"INSERT INTO `tab{target}` ({q}) "
        f"SELECT {expr} FROM `tab{source}` task "
        "WHERE task.reference_doctype = 'CRM Deal' "
        "AND EXISTS (SELECT 1 FROM `tabJob Search Opportunity` d WHERE d.name = task.reference_docname) "
        f"AND NOT EXISTS (SELECT 1 FROM `tab{target}` dst WHERE dst.name = task.name)"
    )


def _remap_history_references():
    """Preserve native Desk activity, attachments and assigned reviews.

    Only remap rows pointing at the already-copied Job Search documents;
    ordinary unrelated CRM records must never be touched.
    """
    changed = {}
    targets = (
        ("CRM Deal", "Job Search Opportunity"),
        ("CRM Task", "Job Search Task"),
        ("CRM Organization", "Job Search Employer"),
    )
    reference_types = (
        ("ToDo", "reference_type", "reference_name"),
        ("File", "attached_to_doctype", "attached_to_name"),
        ("Comment", "reference_doctype", "reference_name"),
        ("Communication", "reference_doctype", "reference_name"),
        ("DocShare", "share_doctype", "share_name"),
        ("Version", "ref_doctype", "docname"),
    )
    for old_type, new_type in targets:
        for document_type, doctype_field, name_field in reference_types:
            if not frappe.db.exists("DocType", document_type):
                continue
            columns = set(frappe.db.get_table_columns(document_type))
            if not {doctype_field, name_field}.issubset(columns):
                continue
            affected = frappe.db.sql(
                f"UPDATE `tab{document_type}` r "
                f"JOIN `tab{new_type}` migrated ON migrated.name = r.`{name_field}` "
                f"SET r.`{doctype_field}` = %s WHERE r.`{doctype_field}` = %s",
                (new_type, old_type),
            )
            changed[f"{document_type}: {old_type}"] = affected
    return changed


def _counts():
    return {
        "opportunities": frappe.db.count("Job Search Opportunity"),
        "employers": frappe.db.count("Job Search Employer"),
        "tasks": frappe.db.count("Job Search Task"),
        "legacy_opportunities": frappe.db.count("CRM Deal", {"js_is_job_search": 1}),
    }


def migrate_from_crm(confirm=False):
    """Invoke using bench execute, only after a complete files+DB backup.

    `confirm=True` is required. Migration is idempotent and does not delete
    original CRM tables, so validation may occur before the uninstall cutover.
    """
    if not frappe.db.exists("DocType", "CRM Deal"):
        frappe.throw("CRM is not installed; run migration before uninstalling CRM")
    if not confirm:
        return {"dry_run": True, "counts": _counts(), "next": "Back up the site and rerun with confirm=True"}
    if frappe.session.user != "Administrator":
        frappe.throw("Run the one-time migration through bench as Administrator", frappe.PermissionError)
    frappe.db.savepoint("job_search_standalone_migration")
    try:
        _copy("CRM Organization", "Job Search Employer", EMPLOYER_WHERE)
        _copy("CRM Deal", "Job Search Opportunity", "src.js_is_job_search = 1")
        _copy_tasks()
        remapped = _remap_history_references()
        # Old CRM business records are not deleted by this operation.
        opp_names = frappe.get_all("Job Search Opportunity", pluck="name")
        # Preserve count/link integrity before any irreversible CRM uninstall.
        orphan_orgs = frappe.db.sql("""
            SELECT d.name FROM `tabJob Search Opportunity` d
            LEFT JOIN `tabJob Search Employer` o ON o.name = d.organization
            WHERE d.organization IS NOT NULL AND d.organization != '' AND o.name IS NULL
        """, as_list=True)
        missing = frappe.db.sql("""
            SELECT c.name FROM `tabCRM Deal` c
            LEFT JOIN `tabJob Search Opportunity` j ON j.name = c.name
            WHERE c.js_is_job_search = 1 AND j.name IS NULL
        """, as_list=True)
        if orphan_orgs or missing:
            frappe.throw(f"Unmigrated records: opportunities={missing}, employers={orphan_orgs}")
        return {
            "verified": True,
            "counts": _counts(),
            "opportunity_names": opp_names,
            "reference_remaps": remapped,
            "note": "CRM remains installed. Verify records and attachments before uninstalling.",
        }
    except Exception:
        frappe.db.rollback(save_point="job_search_standalone_migration")
        raise
