"""Keep Opportunity.applied always in sync with its Application activities.

A persisted indexed Check field supports native Desk filters, list search,
reports and ordinary Frappe database queries without per-read joins or
background reconciliation. MariaDB triggers cover direct child table writes
that do not fire Opportunity DocType hooks.
"""

import frappe

_TRIGGER_PREFIX = 'jsp_sync_opportunity_applied'
_TRIGGERS = (
    f'{_TRIGGER_PREFIX}_ai',
    f'{_TRIGGER_PREFIX}_au',
    f'{_TRIGGER_PREFIX}_ad',
)
_PARENT = '`tabOpportunity`'
_CHILD = '`tabOpportunity Activity`'
_MATCH = "parenttype = 'Opportunity' AND parentfield = 'activity_log' AND type = 'Application'"


def _supported():
    return (getattr(frappe.db, 'db_type', 'mariadb') == 'mariadb'
            and frappe.db.table_exists('Opportunity')
            and frappe.db.table_exists('Opportunity Activity')
            and frappe.db.has_column('Opportunity', 'applied'))


def sync_all_applied():
    """Repair/backfill the stored value from actual activities, idempotently."""
    if not _supported():
        return
    frappe.db.sql(f'''
        UPDATE {_PARENT} AS opportunity
        SET opportunity.applied = EXISTS (
            SELECT 1 FROM {_CHILD} AS activity
            WHERE activity.parent = opportunity.name AND {_MATCH}
        )
        WHERE NOT (opportunity.applied <=> EXISTS (
            SELECT 1 FROM {_CHILD} AS activity
            WHERE activity.parent = opportunity.name AND {_MATCH}
        ))
    ''')


def _update_parent(parent_sql):
    return f'''
        UPDATE {_PARENT} AS opportunity SET opportunity.applied = EXISTS (
            SELECT 1 FROM {_CHILD} AS activity
            WHERE activity.parent = {parent_sql} AND {_MATCH}
        ) WHERE opportunity.name = {parent_sql}
    '''


def ensure_applied_sync():
    """Install low-latency database triggers and backfill existing Opportunities."""
    if not _supported():
        return
    drop_applied_triggers()
    insert, update, delete = _TRIGGERS
    frappe.db.sql_ddl(f'''
        CREATE TRIGGER `{insert}` AFTER INSERT ON {_CHILD}
        FOR EACH ROW BEGIN
            IF NEW.parenttype = 'Opportunity' AND NEW.parentfield = 'activity_log'
                AND NEW.type = 'Application' THEN
                {_update_parent('NEW.parent')};
            END IF;
        END
    ''')
    frappe.db.sql_ddl(f'''
        CREATE TRIGGER `{update}` AFTER UPDATE ON {_CHILD}
        FOR EACH ROW BEGIN
            IF NOT (OLD.parent <=> NEW.parent)
                OR NOT (OLD.type <=> NEW.type)
                OR NOT (OLD.parenttype <=> NEW.parenttype)
                OR NOT (OLD.parentfield <=> NEW.parentfield) THEN
                IF OLD.parenttype = 'Opportunity' AND OLD.parentfield = 'activity_log' THEN
                    {_update_parent('OLD.parent')};
                END IF;
                IF NEW.parenttype = 'Opportunity' AND NEW.parentfield = 'activity_log' THEN
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
    """Remove database objects on uninstall, without touching user data."""
    if (getattr(frappe.db, 'db_type', 'mariadb') or 'mariadb') != 'mariadb':
        return
    for name in _TRIGGERS:
        frappe.db.sql_ddl(f'DROP TRIGGER IF EXISTS `{name}`')
