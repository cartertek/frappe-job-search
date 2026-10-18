"""Idempotently add job fields to CRM's existing Deal layouts, retaining user edits."""

import json

import frappe

QUICK_ENTRY = (
    "js_is_job_search", "js_job_title", "js_posting_url", "js_requisition_id",
    "js_location", "js_employment_type", "js_work_arrangement", "js_seniority",
    "js_deadline", "js_priority",
)
DETAILS = (
    "js_is_job_search", "js_job_title", "js_posting_url", "js_requisition_id",
    "js_employment_type", "js_work_arrangement", "js_location",
    "js_compensation_min", "js_compensation_max", "js_currency",
    "js_compensation_period", "js_seniority", "js_discovered_on", "js_posted_on",
    "js_deadline", "js_qualification", "js_qualification_rationale",
    "js_applied_on", "js_next_action_on", "js_priority", "js_stage",
    "js_closure_reason", "js_offer_details",
    "js_posting_digest", "js_research_digest", "js_agent_recommendation",
    "js_application_review", "js_interview_brief", "js_human_feedback",
    "js_review_request", "js_review_status", "js_review_assigned_to",
    "js_review_task",
    "js_human_action", "js_human_action_rationale",
)
SIDEBAR = (
    "js_is_job_search", "js_job_title", "js_stage", "js_location",
    "js_work_arrangement", "js_posting_url", "js_deadline", "js_next_action_on",
    "js_priority", "js_review_request", "js_review_status",
)


def _load_layout(layout_type):
    name = frappe.db.get_value("CRM Fields Layout", {
        "dt": "CRM Deal", "type": layout_type,
    }, "name")
    if name:
        doc = frappe.get_doc("CRM Fields Layout", name)
        sections = json.loads(doc.layout) if doc.layout else []
    else:
        doc = frappe.get_doc({
            "doctype": "CRM Fields Layout", "dt": "CRM Deal", "type": layout_type,
        })
        if layout_type == "Side Panel":
            # CRM side panel has a purpose-built layout; do not insert all DocType fields.
            sections = []
        else:
            from crm.fcrm.doctype.crm_fields_layout.crm_fields_layout import get_default_layout
            sections = get_default_layout("CRM Deal")
    return doc, sections


def _existing_fields(sections):
    return {
        field for section in sections
        for column in section.get("columns", [])
        for field in column.get("fields", []) if isinstance(field, str)
    }


def ensure_crm_deal_layout():
    """Add Job Opportunity to Create Deal, Data tab and sidebar, without erasing CRM layout."""
    for kind, fields in (
        ("Quick Entry", QUICK_ENTRY), ("Data Fields", DETAILS), ("Side Panel", SIDEBAR),
    ):
        doc, layout = _load_layout(kind)
        if kind == "Side Panel":
            sections = layout
        else:
            if not layout:
                frappe.throw(f"CRM Deal {kind} layout is empty; refusing to overwrite it")
            if "sections" not in layout[0]:
                layout = [{"name": "first_tab", "sections": layout}]
            sections = [section for tab in layout for section in tab.get("sections", [])]

        missing = [field for field in fields if field not in _existing_fields(sections)]
        if not missing:
            continue
        section_name = "job_search_" + kind.lower().replace(" ", "_")
        section = next((s for s in sections if s.get("name") == section_name), None)
        if not section:
            section = {
                "name": section_name, "label": "Job Opportunity", "opened": True,
                "columns": [{"name": section_name + "_column", "fields": []}],
            }
            if kind == "Side Panel":
                layout.append(section)
            else:
                layout[0]["sections"].append(section)
        section["columns"][0]["fields"].extend(missing)
        doc.layout = json.dumps(layout)
        doc.save(ignore_permissions=True)
    frappe.clear_cache()
