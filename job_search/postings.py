"""Immutable publication captures: same source and content is idempotent."""

import hashlib

import frappe
from frappe.utils import now_datetime, nowdate

from job_search.permissions import require_operator, require_opportunity


def content_hash(description):
    # Preserve exact source text. Whitespace/content changes mean a new snapshot.
    return hashlib.sha256((description or "").encode("utf-8")).hexdigest()


def capture_posting(opportunity, *, description, source_name, source_url=None,
                    posting_title=None, requisition_id=None, snapshot=None):
    require_operator()
    deal = require_opportunity(opportunity, "write")
    if not (description or "").strip():
        frappe.throw("Captured full description is required")
    if not (source_name or "").strip():
        frappe.throw("Posting source name is required")
    filters = {"opportunity": deal.name, "source_name": source_name}
    if source_url:
        filters["source_url"] = source_url
    else:
        filters["source_url"] = ["is", "not set"]
    latest = frappe.db.get_value("Job Search Posting", filters,
                                 ["name", "content_hash"], order_by="creation desc", as_dict=True)
    digest = content_hash(description)
    if latest and latest.content_hash == digest:
        if deal.get("latest_posting") != latest.name:
            deal.posting_text = description
            deal.latest_posting = latest.name
            deal.save()
        return {"posting": latest.name, "created": False}
    # If text changed and later reverted, preserve the third observation as a new revision.
    preceding = latest.name if latest else None
    entry = frappe.get_doc({
        "doctype": "Job Search Posting", "opportunity": deal.name,
        "organization": deal.organization, "source_name": source_name,
        "source_url": source_url, "posting_title": posting_title or deal.job_title,
        "requisition_id": requisition_id or deal.requisition_id,
        "description": description, "snapshot": snapshot,
        "supersedes": preceding, "retrieved_on": now_datetime(),
        "first_observed": nowdate(), "last_observed": nowdate(), "status": "Unknown",
    }).insert()
    # Publish the latest immutable capture into the human's Job Search Opportunity Data tab.
    # Older versions stay in Job Search Posting and are never overwritten.
    deal.posting_text = description
    deal.latest_posting = entry.name
    deal.save()
    return {"posting": entry.name, "created": True, "supersedes": preceding}
