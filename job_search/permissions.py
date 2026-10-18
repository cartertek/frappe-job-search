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
    doc = require_doc("Job Search Opportunity", name, ptype)
    return doc


def require_operator():
    check_role("Job Search Operator", "Job Search Approver", "System Manager")


def require_approver():
    check_role("Job Search Approver", "System Manager")


def can_access_app():
    """Frappe Apps-screen visibility hook; must return a bool, not throw."""
    return frappe.session.user != "Guest" and bool(
        {"Job Search Operator", "Job Search Approver", "System Manager"}
        & set(frappe.get_roles(frappe.session.user))
    )
