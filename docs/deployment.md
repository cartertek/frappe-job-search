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

# Deployment and migration

Install `job_search` on Frappe v16; no CRM is needed for the current platform. **Never** run a destructive DocType migration against production before validating it on an isolated copy of a current production backup.

## Job/Opportunity split — issue #15

Before migration, preserve a verified database + file backup and baseline counts/IDs for `Job Search Opportunity`, `Job Search Employer`, `Job Search Posting`, `Job Search Source`, `Job Search Research`, `Job Search Transition`, `Job Search Decision`, `Job Search Application`, `Job Search Interview`, `Job Search Task`, procedure executions, and memberships. The pre-sync patch `job_search.patches.v5_split_opportunities` renames the old job-like DocType into **Job** (retaining its existing IDs and linked descriptions). The after-migrate backfill creates matching **Opportunity** records and **Opportunity Job** child rows for each historical Job and restores Opportunity lifecycle data. All cross-links are checked; data is not merged based on employer name. The v5 split is idempotent through `job_search:opportunity_split_v5`. The guarded v6 cleanup additionally merges only compatible historical duplicate Opportunities within each Organization, stores **Opportunity Consolidation** snapshots of source histories, retains every Job, transfers Job tags onto each remaining Opportunity using Frappe's tag API, and initializes Job availability from the latest saved Posting status (`Active` → Active, `Removed` or `Expired` → Closed, unknown → Unknown). The captured Posting status is the last observed state, **not a claim that it has been reverified today**. The cleanup is idempotent through `job_search:opportunity_cleanup_v6`. Existing explicitly separate hiring teams and conflicting human decisions fail closed; investigate rather than forcing a merge.

Current Job availability defaults to **Unknown** unless separately verified Active; historical pursuit stages, decisions and annotations remain on the newly created Opportunities. Existing Posting rows receive a `job` link while retaining their Opportunity references. Job-specific sources/research may also be linked to Job without discarding historical Opportunity IDs. Applications/interviews/offers/tasks/transitions retain the same Opportunity document ID as before. No human decisions are created by migration.

Run after the migration:

```sh
bench --site YOUR-SITE execute job_search.opportunity_migration.verify_opportunity_migration
bench --site YOUR-SITE execute job_search.desktop_integrity.audit_desktop_layouts --kwargs '{"strict": True}'
bench --site YOUR-SITE clear-cache
```

Compare the post-migration record counts and IDs with the backup, then open real migrated Job and Opportunity records, verify their historical linked records and permissions, and exercise the Search Results UI. Repeat `bench migrate` to ensure no duplication. The migration has been tested with a copy of 23 Jobs and their historical records; do not assume that the same verification covers new or future records without checking them.

## Desktop icon regression checks

Frappe Desktop Icons mode has **two independent sources**: `Desktop Icon` records used to build the permitted boot icons, and each person's saved `Desktop Layout` (a snapshot of icon names, folders and ordering). A missing `Desktop Icon` or an invalid `parent_icon` can make an entry disappear even when the layout still lists it. Frappe's migration orphan cleanup only removes missing-file **standard** desktop icons; custom icons can disappear from view without being deleted.

After any deployment/migration involving Desk, apps, desktop icons, or workspaces, run the read-only smoke check:

```sh
bench --site YOUR-SITE execute job_search.desktop_integrity.audit_desktop_layouts --kwargs '{"strict": True}'
```

A nonzero exit code indicates a broken icon parent, a saved icon without an accessible backing icon, or an icon not shared with its layout owner. **Do not reset a user's layout to fix this.** Back up the site and reconcile the `Desktop Icon` and *that user's* `Desktop Layout` by stable icon name, preserving position and folder, using the assistant's own account for any authorized edit; never impersonate a user or Administrator. For live migrations `after_migrate` runs the same audit in warning-only mode so upgrades don't fail because an unrelated private layout is stale. Frappe core is the owner of duplicate-icon cleanup. The platform image applies a generic safeguard preventing `delete_duplicate_icons()` from deleting nonstandard (`standard=0`) icons; do not restore hard-coded parent names in an application migration. If a historical icon has already been deleted, recover the specific icon and corresponding saved layout from backups or the Deleted Document history, preserving the user-defined arrangement.
