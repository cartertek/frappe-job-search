# Known limitations and remaining validation

- Not yet installed or tested on a writable Frappe/CRM test site. Schema and Python static validation do not verify Frappe install, CRM frontend field rendering, migrations or upgrades.
- The inspected SEI bench runs Frappe 17.0.0-dev / CRM 2.0.0-dev. No tested stable version or exact commit pair is pinned yet.
- Public CRM saved Deal views are seeded but still require live frontend verification. Desk navigation exists; custom unified dossier pages and queue pages do not. Operator APIs return linked records.
- No applications are submitted or messages sent, and no job board scraping is attempted.
- Re-registering a posting URL does not snapshot new content at the same URL automatically. Use a separate Job Search Posting record to capture changed text.
- Active published procedures cannot be edited or retired in-place; create a new version.
- Operator role does not implicitly grant the necessary CRM roles. Keep approver and operator credentials separate.
- Stage entry currently does not automatically create follow-up tasks; an explicit CRM Task API is available. Automated alerts, aging notifications and reporting remain future work.
- Direct database writes bypass Frappe document hooks and must not be used to mutate the workflow.
- CI covers static checks. MariaDB integration, API tests against an installed bench, and backup/restore tests remain outstanding.

- Rejected, Withdrawn and Closed use CRM Deal Status type On Hold to avoid forcing unrelated sales Lost Reason fields; their Job Search stage still represents the exact outcome. Sites relying on CRM native sales forecasting must validate the Deal semantics independently.
