"""Retain configured criteria from searches created before issue #1."""

import frappe


def execute():
    table = 'tabJob Search Search'
    columns = set(frappe.db.get_table_columns('Job Search Search'))
    for old, new in (('title_contains', 'title_matches'), ('location_contains', 'location_match')):
        if old in columns and new in columns:
            frappe.db.sql(
                f"UPDATE `{table}` SET `{new}` = `{old}` "
                f"WHERE COALESCE(`{new}`, '') = '' AND COALESCE(`{old}`, '') != ''"
            )
