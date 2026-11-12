"""Read-only integrity checks for Frappe Desktop Icon and saved Desktop Layout data.

Desktop layouts are *snapshots* of icon names, parent relationships and ordering;
the server filters unavailable icons from its boot payload. A missing icon or an
orphaned parent can therefore disappear without deleting the saved layout row.
"""

import json


def find_desktop_layout_issues(icons, layouts, private_workspaces=()):
    """Report inaccessible saved icons and broken parent references.

    `icons` contains Desktop Icon dictionaries (including owner and standard).
    `layouts` maps user ID to their decoded Desktop Layout list. No writes.
    """
    by_name = {icon["name"]: icon for icon in icons}
    by_label = {icon.get("label"): icon for icon in icons}
    private = set(private_workspaces)
    issues = []

    for icon in icons:
        parent = icon.get("parent_icon")
        if parent and parent not in by_name and parent not in by_label:
            issues.append({"kind": "missing_database_parent", "icon": icon["name"], "parent": parent})

    for user, rows in layouts.items():
        for row in rows:
            identity = row.get("name") or row.get("label")
            icon = by_name.get(row.get("name")) or by_label.get(row.get("label"))
            if not icon:
                issues.append({"kind": "missing_saved_icon", "user": user, "icon": identity})
                continue
            # Corresponds to the Desktop Icon grid's initial owner/share filter.
            visible = (bool(icon.get("standard")) or icon.get("owner") in ("Administrator", user)
                       or (icon.get("icon_type") == "Link" and icon.get("link_to") not in private))
            if not visible:
                issues.append({"kind": "unshared_saved_icon", "user": user, "icon": identity})
            parent = icon.get("parent_icon")
            if parent and parent not in by_name and parent not in by_label:
                issues.append({"kind": "unavailable_database_parent", "user": user, "icon": identity,
                               "parent": parent})
            parent = row.get("parent_icon")
            names = {r.get("name") for r in rows}
            labels = {r.get("label") for r in rows}
            if parent and parent not in names and parent not in labels:
                issues.append({"kind": "missing_saved_parent", "user": user, "icon": identity,
                               "parent": parent})
    return issues


def audit_desktop_layouts(strict=False):
    """Audit production records after migration; never alter user desktop layouts."""
    import frappe

    if not (frappe.db.exists("DocType", "Desktop Icon")
            and frappe.db.exists("DocType", "Desktop Layout")):
        return []
    icons = [dict(row) for row in frappe.get_all("Desktop Icon", fields=[
        "name", "label", "parent_icon", "standard", "owner", "icon_type", "link_to"],
        limit_page_length=10000)]
    layouts = {}
    for row in frappe.get_all("Desktop Layout", fields=["name", "user", "layout"],
                              limit_page_length=10000):
        if row.layout:
            try:
                layouts[row.user or row.name] = json.loads(row.layout)
            except (ValueError, TypeError):
                layouts[row.user or row.name] = []
                frappe.logger("job_search").warning("Invalid saved Desktop Layout: %s", row.name)

    private = set(frappe.get_all("Workspace", filters={"public": 0}, pluck="name"))
    issues = find_desktop_layout_issues(icons, layouts, private)
    if issues:
        if strict:
            raise RuntimeError(f"Desktop layout integrity failed: {json.dumps(issues)}")
        frappe.logger("job_search").warning("Desktop layout integrity: %s", json.dumps(issues))
        print(f"WARNING: {len(issues)} desktop layout integrity issue(s): {json.dumps(issues)}")
    else:
        print(f"Desktop layout integrity: OK ({len(icons)} icons, {len(layouts)} saved layouts)")
    return issues
