# Architecture

The app owns the Job Search DocTypes and narrowly scoped CRM fixtures. It does not fork, edit, or monkey-patch CRM source. CRM Deal is the opportunity; CRM Organization is the employer; the Frappe Contact DocType is linked through CRM Contacts child rows; CRM Task handles follow-ups.

Standard Frappe DocType metadata/controllers live in job_search/job_search/doctype. Job Search Desk navigation uses Workspace, Workspace Sidebar and Desktop Icon metadata modeled after SEI. Migration hooks seed only missing namespaced CRM Deal Status values and procedure versions. They never rewrite published procedures or research data.

The authoritative CRM Deal validation hook enforces stage and status consistency, documented prerequisites, and approvals on ordinary UI/REST document saves. The server generates immutable transition history. Low-level database mutations bypass Frappe hooks and must not be used for workflow changes.

Signed-in Job Search Approvers create immutable Job Search Decisions; the operator can reference decisions but cannot create them. Normal Frappe and CRM permissions apply to resource CRUD; custom whitelisted methods check permissions explicitly. No operator method sends an application or email.

Procedure definitions are committed as versioned source JSON in job_search/setup/procedures.json. Install/migrate creates missing procedure versions without changing published ones; executions retain procedure identity, version and a step snapshot.
