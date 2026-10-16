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
