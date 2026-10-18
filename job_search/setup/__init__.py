"""Install and migrate only app-owned configuration, never user research."""

import json
from pathlib import Path

import frappe

from job_search.workflow import STAGES, status_name


def after_install():
    after_migrate()


def after_migrate():
    """Idempotently create stage metadata and seed *new* procedure versions."""
    for index, stage in enumerate(STAGES):
        name = status_name(stage)
        if not frappe.db.exists("CRM Deal Status", name):
            frappe.get_doc({
                "doctype": "CRM Deal Status",
                "deal_status": name,
                "position": 100 + index,
                "type": "Won" if stage == "Accepted" else (
                    "On Hold" if stage in ("Rejected", "Withdrawn", "Closed") else "Ongoing"
                ),
                "color": "green" if stage == "Accepted" else (
                    "red" if stage in ("Rejected", "Withdrawn", "Closed") else "blue"
                ),
            }).insert(ignore_permissions=True)  # migration-only configuration
    ensure_crm_views()
    from job_search.setup.crm_layout import ensure_crm_deal_layout

    ensure_crm_deal_layout()
    path = Path(__file__).with_name("procedures.json")
    for item in json.loads(path.read_text()):
        if frappe.db.exists("Job Search Procedure", {
            "procedure_id": item["procedure_id"], "version": item["version"],
        }):
            continue  # Published versions are immutable; never silently edit them.
        frappe.get_doc({"doctype": "Job Search Procedure", **item}).insert(
            ignore_permissions=True
        )  # migration-only seed data
    frappe.clear_cache()

def ensure_crm_views():
    """Create scoped public CRM Deal views once; never overwrite user changes."""
    templates = (
        (
            "Job Search Pipeline",
            "kanban",
            {"js_is_job_search": 1},
            "status",
            [{"name": status_name(stage)} for stage in STAGES],
        ),
        (
            "Job Search Human Review", "list",
            {"js_is_job_search": 1, "js_review_status": "Pending"},
            None, [],
        ),
        (
            "Job Search Research Queue",
            "list",
            {"js_is_job_search": 1, "js_stage": "Researching"},
            None,
            [],
        ),
    )
    for label, view_type, filters, column, kanban_columns in templates:
        if frappe.db.exists("CRM View Settings", {"label": label, "dt": "CRM Deal", "public": 1}):
            continue
        frappe.get_doc({
            "doctype": "CRM View Settings",
            "label": label, "dt": "CRM Deal", "route_name": "Deals",
            "type": view_type, "column_field": column,
            "filters": json.dumps(filters),
            "kanban_columns": json.dumps(kanban_columns),
            "columns": json.dumps([]), "rows": json.dumps([]),
            "user": "", "public": 1, "is_standard": 1,
            "order_by": "modified desc",
        }).insert(ignore_permissions=True)  # app-scoped migration config
