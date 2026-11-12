# Deployment

For new sites, install `job_search` directly into Frappe v16. The app has no
CRM dependency. On existing CRM-backed sites, **back up first**, migrate the app
and historical data while CRM remains installed, verify imported records, then
uninstall CRM and deploy the CRM-free image. Full commands appear in the README
and in the `job_search_platform` OPERATIONS runbook.

Verify the `Job Search` Desk Workspace, Opportunity/Employer/Task forms, review
modal, stage transitions, source-backed research, history, task idempotency,
application authorization and interview workflows. Do not use raw database
writes for operational workflow stage changes; only the historical importer
uses SQL to retain original record identifiers and timestamps.

## Desktop icon regression checks

Frappe Desktop Icons mode has **two independent sources**: `Desktop Icon` records used to build the permitted boot icons, and each person's saved `Desktop Layout` (a snapshot of icon names, folders and ordering). A missing `Desktop Icon` or an invalid `parent_icon` can make an entry disappear even when the layout still lists it. Frappe's migration orphan cleanup only removes missing-file **standard** desktop icons; custom icons can disappear from view without being deleted.

After any deployment/migration involving Desk, apps, desktop icons, or workspaces, run the read-only smoke check:

```sh
bench --site YOUR-SITE execute job_search.desktop_integrity.audit_desktop_layouts --kwargs '{"strict": True}'
```

A nonzero exit code indicates a broken icon parent, a saved icon without an accessible backing icon, or an icon not shared with its layout owner. **Do not reset a user's layout to fix this.** Back up the site and reconcile the `Desktop Icon` and *that user's* `Desktop Layout` by stable icon name, preserving position and folder, using the assistant's own account for any authorized edit; never impersonate a user or Administrator. For live migrations `after_migrate` runs the same audit in warning-only mode so upgrades don't fail because an unrelated private layout is stale. Frappe core is the owner of duplicate-icon cleanup. The platform image applies a generic safeguard preventing `delete_duplicate_icons()` from deleting nonstandard (`standard=0`) icons; do not restore hard-coded parent names in an application migration. If a historical icon has already been deleted, recover the specific icon and corresponding saved layout from backups or the Deleted Document history, preserving the user-defined arrangement.
