"""Synchronize stored Opportunity-derived fields from its Activity Log.

MariaDB triggers cover insert, update (including Contact and Date changes),
reparent and deletion performed outside the parent document lifecycle.
The stored, indexed fields support native list filtering and sorting.
"""

import frappe

_TRIGGER_PREFIX = 'jsp_sync_opportunity_applied'
_TRIGGERS = tuple(f'{_TRIGGER_PREFIX}_{suffix}' for suffix in ('ai', 'au', 'ad'))
_PARENT = '`tabOpportunity`'
_CHILD = '`tabOpportunity Activity`'
_MATCH = "parenttype = 'Opportunity' AND parentfield = 'activity_log'"
_APPLICATION = _MATCH + " AND type = 'Application'"


def _supported():
    return (getattr(frappe.db, 'db_type', 'mariadb') == 'mariadb'
            and frappe.db.table_exists('Opportunity')
            and frappe.db.table_exists('Opportunity Activity')
            and all(frappe.db.has_column('Opportunity', field)
                    for field in ('applied', 'applied_on', 'common_contact')))


def _derived_assignments(parent_sql):
    condition = f'activity.parent = {parent_sql} AND '
    return f'''
        opportunity.applied = EXISTS (
            SELECT 1 FROM {_CHILD} activity WHERE {condition}{_APPLICATION}
        ),
        opportunity.applied_on = (
            SELECT MAX(activity.date) FROM {_CHILD} activity
            WHERE {condition}{_APPLICATION}
        ),
        opportunity.common_contact = (
            SELECT TRIM(activity.contact) FROM {_CHILD} activity
            WHERE {condition}{_MATCH}
                AND activity.contact IS NOT NULL AND TRIM(activity.contact) != ''
            GROUP BY TRIM(activity.contact)
            ORDER BY COUNT(*) DESC, TRIM(activity.contact) ASC
            LIMIT 1
        )
    '''


def sync_all_applied():
    """Recompute all three derived fields from stored Activity rows."""
    if not _supported():
        return
    frappe.db.sql(f'''
        UPDATE {_PARENT} AS opportunity
        SET {_derived_assignments('opportunity.name')}
    ''')


def _update_parent(parent_sql):
    return f'''
        UPDATE {_PARENT} AS opportunity
        SET {_derived_assignments(parent_sql)}
        WHERE opportunity.name = {parent_sql}
    '''


def ensure_applied_sync():
    """Idempotently install triggers and backfill existing Opportunities."""
    if not _supported():
        return
    drop_applied_triggers()
    insert, update, delete = _TRIGGERS
    frappe.db.sql_ddl(f'''
        CREATE TRIGGER `{insert}` AFTER INSERT ON {_CHILD}
        FOR EACH ROW BEGIN
            IF NEW.parenttype = 'Opportunity' AND NEW.parentfield = 'activity_log' THEN
                {_update_parent('NEW.parent')};
            END IF;
        END
    ''')
    frappe.db.sql_ddl(f'''
        CREATE TRIGGER `{update}` AFTER UPDATE ON {_CHILD}
        FOR EACH ROW BEGIN
            IF NOT (OLD.parent <=> NEW.parent)
                OR NOT (OLD.type <=> NEW.type)
                OR NOT (OLD.date <=> NEW.date)
                OR NOT (OLD.contact <=> NEW.contact)
                OR NOT (OLD.parenttype <=> NEW.parenttype)
                OR NOT (OLD.parentfield <=> NEW.parentfield) THEN
                IF OLD.parenttype = 'Opportunity' AND OLD.parentfield = 'activity_log' THEN
                    {_update_parent('OLD.parent')};
                END IF;
                IF NEW.parenttype = 'Opportunity' AND NEW.parentfield = 'activity_log'
                    AND (NOT (OLD.parent <=> NEW.parent)
                         OR NOT (OLD.parenttype <=> NEW.parenttype)
                         OR NOT (OLD.parentfield <=> NEW.parentfield)) THEN
                    {_update_parent('NEW.parent')};
                END IF;
            END IF;
        END
    ''')
    frappe.db.sql_ddl(f'''
        CREATE TRIGGER `{delete}` AFTER DELETE ON {_CHILD}
        FOR EACH ROW BEGIN
            IF OLD.parenttype = 'Opportunity' AND OLD.parentfield = 'activity_log' THEN
                {_update_parent('OLD.parent')};
            END IF;
        END
    ''')
    sync_all_applied()


def drop_applied_triggers():
    """Drop only app-owned triggers when uninstalling the app."""
    if getattr(frappe.db, 'db_type', 'mariadb') != 'mariadb':
        return
    for name in _TRIGGERS:
        frappe.db.sql_ddl(f'DROP TRIGGER IF EXISTS `{name}`')
