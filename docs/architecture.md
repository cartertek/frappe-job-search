# Architecture

The app owns the Job Search DocTypes and narrowly scoped CRM fixtures. It does not fork, edit, or monkey-patch CRM source. CRM Deal is the opportunity; CRM Organization is the employer; the Frappe Contact DocType is linked through CRM Contacts child rows; CRM Task handles follow-ups.

Standard Frappe DocType metadata/controllers live in `job_search/job_search/doctype`. CRM Deal Quick Entry is extended using CRM Fields Layout; no separate Desk workspace, Dock, Sidebar, or app shell is installed. Migration hooks seed only missing namespaced CRM Deal Status values and procedure versions. They never rewrite published procedures or research data.

The authoritative CRM Deal validation hook enforces stage and status consistency, documented prerequisites, and approvals on ordinary UI/REST document saves. The server generates immutable transition history. Low-level database mutations bypass Frappe hooks and must not be used for workflow changes.

Signed-in Job Search Approvers create immutable Job Search Decisions; the operator can reference decisions but cannot create them. Normal Frappe and CRM permissions apply to resource CRUD; custom whitelisted methods check permissions explicitly. No operator method sends an application or email.

Procedure definitions are committed as versioned source JSON in job_search/setup/procedures.json. Install/migrate creates missing procedure versions without changing published ones; executions retain procedure identity, version and a step snapshot.

## Operational workflow additions

Each stage change records a durable Job Search Transition. For actionable stages, the same transaction creates a CRM Task linked to both the Deal and source transition (`CRM Task.js_transition`). An existing task with that transition is reused instead of duplicated. Tasks are never emails or external submissions. The latest application date is synchronized back to its CRM Deal using a normal Document save.

Full posting text is immutable once captured; its SHA-256 content hash and `supersedes` link preserve repeated observations of changing listings. Company-level and opportunity-level research remains separately associated, with classified evidence quality and source links. The operator API provides company dossiers, research queues and upcoming/overdue follow-ups using the normal Frappe permission-aware query methods.
