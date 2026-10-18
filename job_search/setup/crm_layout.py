"""CRM-native Deal quick entry extension; retain all existing user layout sections."""

import json

import frappe

JOB_SEARCH_FIELDS = (
    "js_is_job_search", "js_job_title", "js_posting_url", "js_requisition_id",
    "js_location", "js_employment_type", "js_work_arrangement", "js_seniority",
    "js_deadline", "js_priority",
)


def ensure_crm_deal_layout():
    """Append job fields to CRM's configurable quick entry, without replacing sales fields."""
    name = frappe.db.get_value("CRM Fields Layout", {"dt": "CRM Deal", "type": "Quick Entry"}, "name")
    if name:
        doc = frappe.get_doc("CRM Fields Layout", name)
        tabs = json.loads(doc.layout) if doc.layout else []
    else:
        from crm.fcrm.doctype.crm_fields_layout.crm_fields_layout import get_default_layout
        tabs = get_default_layout("CRM Deal")
        doc = frappe.get_doc({"doctype": "CRM Fields Layout", "dt": "CRM Deal", "type": "Quick Entry"})

    if not tabs:
        frappe.throw("CRM Deal quick entry layout is empty; refusing to replace it")
    if "sections" not in tabs[0]:
        tabs = [{"name": "first_tab", "sections": tabs}]
    existing = {
        field
        for tab in tabs for section in tab.get("sections", [])
        for column in section.get("columns", [])
        for field in column.get("fields", [])
        if isinstance(field, str)
    }
    missing = [field for field in JOB_SEARCH_FIELDS if field not in existing]
    if not missing:
        return
    tab = tabs[0]
    section = next((s for s in tab["sections"] if s.get("name") == "job_search_quick_entry"), None)
    if not section:
        section = {"name": "job_search_quick_entry", "label": "Job Opportunity",
                   "columns": [{"name": "job_search_column", "fields": []}]}
        tab["sections"].append(section)
    section["columns"][0]["fields"].extend(missing)
    doc.layout = json.dumps(tabs)
    doc.save(ignore_permissions=True)
    frappe.clear_cache()
