# Known limitations and remaining validation

- Installed and successfully migrated on `jobsearch.localhost` (Frappe 16.52.0 / CRM 1.88.0). Transaction-rolled-back end-to-end and separate-role runtime checks passed. A clean-site install, real browser acceptance, and automated CI tests against Frappe/MariaDB remain outstanding.
- Compatibility review uses Frappe v16.52.0 (`version-16`, source commit 4515014) and Frappe CRM v1.88.0 (`main`, source commit 0baa1e8), and the deployed stack has passed migrations and transaction-rolled-back runtime tests. The target is the latest compatible releases on these stable branches; not a previously tested exact pair.
- CRM Quick Entry, Data, Side Panel and public Deal views have been installed and their server responses verified. Actual human browser interaction, mobile behavior, and review usability still need acceptance testing.
- No applications are submitted or messages sent, and no job board scraping is attempted.
- Posting revisions are stored when updated descriptions are passed through register_opportunity or capture_posting. Automatic polling/scraping is still out of scope.
- Active published procedures cannot be edited or retired in-place; create a new version.
- Operator role does not implicitly grant the necessary CRM roles. Keep approver and operator credentials separate.
- Actionable stage entry generates a linked CRM Task; work-queue APIs group overdue/freshness data. Scheduled notifications, comprehensive reporting, and custom queue UIs remain future work.
- Direct database writes bypass Frappe document hooks and must not be used to mutate the workflow.
- CI covers structural and isolated behavior checks. Live Frappe/MariaDB workflow and two-role smoke checks passed manually, but automated integration CI, permission-regression coverage, and backup/restore remain outstanding.

- Rejected, Withdrawn and Closed use CRM Deal Status type On Hold to avoid forcing unrelated sales Lost Reason fields; their Job Search stage still represents the exact outcome. Sites relying on CRM native sales forecasting must validate the Deal semantics independently.
