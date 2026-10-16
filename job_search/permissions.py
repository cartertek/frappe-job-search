import frappe


def check_role(*roles):
    if frappe.session.user == "Guest":
        frappe.throw("Authentication required", frappe.PermissionError)
    if not set(roles).intersection(frappe.get_roles(frappe.session.user)):
        frappe.throw("Job Search role required: " + ", ".join(roles), frappe.PermissionError)


def require_doc(doctype, name, ptype="read"):
    doc = frappe.get_doc(doctype, name)
    doc.check_permission(ptype)
    return doc


def require_opportunity(name, ptype="read"):
    doc = require_doc("CRM Deal", name, ptype)
    if not doc.get("js_is_job_search"):
        frappe.throw("This Deal is not a Job Search opportunity")
    return doc


def require_operator():
    check_role("Job Search Operator", "Job Search Approver", "System Manager")


def require_approver():
    check_role("Job Search Approver", "System Manager")
