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
