# Known limitations and remaining validation

- Not yet installed or tested on a writable Frappe/CRM test site. Schema and Python static validation do not verify Frappe install, CRM frontend field rendering, migrations or upgrades.
- Compatibility review uses Frappe v16.52.0 (`version-16`, source commit 4515014) and Frappe CRM v1.88.0 (`main`, source commit 0baa1e8), but neither stack has passed a live app install here. The target is the latest compatible releases on these stable branches; not a previously tested exact pair.
- Public CRM views and the CRM Quick Entry layout additions need live frontend verification. There are no custom dossier/queue UI pages; read-only operator endpoints provide the corresponding data.
- No applications are submitted or messages sent, and no job board scraping is attempted.
- Posting revisions are stored when updated descriptions are passed through register_opportunity or capture_posting. Automatic polling/scraping is still out of scope.
- Active published procedures cannot be edited or retired in-place; create a new version.
- Operator role does not implicitly grant the necessary CRM roles. Keep approver and operator credentials separate.
- Actionable stage entry generates a linked CRM Task; work-queue APIs group overdue/freshness data. Scheduled notifications, comprehensive reporting, and custom queue UIs remain future work.
- Direct database writes bypass Frappe document hooks and must not be used to mutate the workflow.
- CI covers structural tests and isolated behavioral tests for posting revisions, stage-task idempotency and date bucketing. MariaDB/Frappe integration, permissions tests on a live bench, and backup/restore remain outstanding.

- Rejected, Withdrawn and Closed use CRM Deal Status type On Hold to avoid forcing unrelated sales Lost Reason fields; their Job Search stage still represents the exact outcome. Sites relying on CRM native sales forecasting must validate the Deal semantics independently.
