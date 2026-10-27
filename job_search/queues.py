"""Read-only operational queues using native Frappe permission-aware get_list."""

from datetime import timedelta

import frappe
from frappe.utils import getdate, nowdate

from job_search.permissions import require_operator

OPEN_STAGES = ["Discovered", "Researching", "Qualified", "Preparing", "Applied",
               "Screening", "Interviewing", "Offer"]


def classify_due(due_date, today, horizon=14):
    if not due_date:
        return "unscheduled"
    date = getdate(due_date)
    current = getdate(today)
    if date < current:
        return "overdue"
    if date <= current + timedelta(days=horizon):
        return "upcoming"
    return "later"


def follow_up_queue(horizon=14):
    require_operator()
    horizon = int(horizon)
    if not 0 <= horizon <= 365:
        frappe.throw("Horizon must be between 0 and 365 days")
    deals = frappe.get_list("Job Search Opportunity", filters={},
        fields=["name", "job_title", "organization"], limit_page_length=1000)
    names = {d.name for d in deals}
    tasks = frappe.get_list("Job Search Task", filters={
        "status": ["not in", ["Done", "Canceled"]],
    }, fields=["name", "title", "status", "due_date", "assigned_to", "opportunity"],
        limit_page_length=2000)
    buckets = {"overdue": [], "upcoming": [], "later": [], "unscheduled": []}
    today = nowdate()
    for task in tasks:
        if task.opportunity in names:
            buckets[classify_due(task.due_date, today, horizon)].append(task)
    for records in buckets.values():
        records.sort(key=lambda t: (str(t.due_date or "9999"), t.name))
    return {"as_of": today, "horizon_days": horizon, **buckets}


def research_queue(stale_after_days=90):
    require_operator()
    stale_after_days = int(stale_after_days)
    if not 1 <= stale_after_days <= 3650:
        frappe.throw("Research freshness threshold must be between 1 and 3650 days")
    deals = frappe.get_list("Job Search Opportunity", filters={        "status": ["in", OPEN_STAGES]},
        fields=["name", "organization", "job_title", "status", "priority"],
        limit_page_length=1000)
    research = frappe.get_list("Job Search Research",
        fields=["name", "opportunity", "organization", "status", "last_verified",
                "evidence_class", "modified"], limit_page_length=3000)
    cutoff = getdate(nowdate()) - timedelta(days=stale_after_days)
    by_deal = {}
    by_org = {}
    for r in research:
        if r.opportunity:
            by_deal.setdefault(r.opportunity, []).append(r)
        elif r.organization:
            by_org.setdefault(r.organization, []).append(r)
    result = []
    for d in deals:
        items = by_deal.get(d.name, []) + by_org.get(d.organization, [])
        verified = [r for r in items if r.status == "Verified"
                    and r.evidence_class in ("Verified Fact", "Supported Interpretation")]
        stale = [r for r in items if r.status == "Stale" or
                 (r.last_verified and getdate(r.last_verified) < cutoff)]
        reasons = []
        if not items:
            reasons.append("No research")
        elif not verified:
            reasons.append("No verified research")
        if stale:
            reasons.append("Research needs re-verification")
        if d.status in ("Discovered", "Researching"):
            reasons.append("Research stage outstanding")
        if reasons:
            result.append({"opportunity": d.name, "organization": d.organization,
                           "job_title": d.job_title, "stage": d.status,
                           "priority": d.priority, "reasons": reasons,
                           "research_records": [r.name for r in items],
                           "stale_records": [r.name for r in stale]})
    return {"as_of": nowdate(), "stale_after_days": stale_after_days, "queue": result}
