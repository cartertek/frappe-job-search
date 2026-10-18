# Standalone architecture

The app runs on Frappe v16 without Frappe CRM. It owns Job Search Opportunity,
Employer and Task DocTypes and all posting, research, source, procedure, execution,
application, interview, transition and human-decision models. Frappe's built-in
User, Contact, File, Comment and ToDo models remain available.

The human UI is a standard Desk Workspace and the Job Search Opportunity form.
Pending human reviews have a **Record Decision** custom button which opens a
native `frappe.ui.Dialog`; it calls `record_human_decision`. The server alone
creates immutable signed Job Search Decision records, closes review tasks,
and closes declined opportunities. These one-time inputs are hidden in the
persistent form; the human sees the saved last decision and review status.

Agents call the whitelisted `job_search.api` endpoints to create opportunities,
append original posting text/revisions, cite research, complete versioned
procedures and request human approval. Permission checks enforce the operator
and approver roles; saving a stage through Frappe ORM runs the same server-side
workflow validation as the API. A stage transition generates a retained event
and, where appropriate, an idempotent Job Search Task.

The explicit `job_search.migration.migrate_from_crm` imports historical CRM-backed
opportunities, employers and tasks preserving original document names. It then
remaps native Frappe activity and assignment references for the imported rows.
CRM stays installed until the import and user acceptance are verified.
