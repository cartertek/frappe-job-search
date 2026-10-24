"""Column migration is handled after schema synchronization in setup.

Frappe executes patch files before DocType sync; the matching field data is
copied by `job_search.setup.migrate_legacy_search_filters` in after_migrate.
"""


def execute():
    pass
