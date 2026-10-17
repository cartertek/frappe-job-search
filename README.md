# Frappe Job Search

A standalone Frappe app extending Frappe CRM with a structured, source-backed job-search workflow. It follows Cartertek's SEI conventions: standard DocTypes/controllers, narrowly scoped CRM Custom Field fixtures, migration-managed configuration, whitelisted service methods, and version-controlled procedures.

**Package:** job_search. **Dependency:** Frappe CRM (crm). **Compatibility target:** Latest stable **Frappe `version-16`**, currently v16.52.0 (October 14, 2026), paired with stable **Frappe CRM `main`**, currently v1.88.0 (October 15, 2026), on Python 3.14. These sources were inspected; a live integration test is still required.

## Features

- CRM Deal as the job opportunity with js_is_job_search, employer link, position details, and namespaced JS: stage status values.
- Employer fields on CRM Organization; Frappe Contact and CRM Task reused.
- Durable records for Posting, Source, Research, Procedure, Procedure Execution, Application, Interview, Decision, and Transition.
- Source evidence, original job descriptions, historical applications, immutable human approvals, completed procedure steps, and stage transitions.
- Server-side validation for CRM Deal status edits, whether from CRM UI, Desk, or standard document REST.
- Frappe 16.50+ Apps → Dock → Module Sidebar navigation and a Job Search Workspace.
- Automated, idempotent CRM Tasks on stage entry; API research/follow-up queues and a company dossier.
- Posting snapshots retain their full original description. Changed descriptions append an immutable linked revision.
- Operator API. No automated application submission or outbound email.

## Installation (on a separate test site first)

In the bench directory:

    bench get-app https://github.com/cartertek/frappe-job-search --branch main
    bench --site TEST-SITE install-app crm  # only if not already installed
    bench --site TEST-SITE install-app job_search
    bench --site TEST-SITE migrate

Assign **Job Search Operator** and an appropriate CRM Sales role (for Deal/Organization/Task permissions) to a dedicated non-Administrator operator user. Assign **Job Search Approver** only to actual human approvers. Approvers also need CRM permissions for their interactions.

Frappe Desk has a Job Search app, Dock, module Sidebar and Workspace. The app seeds public Job Search Pipeline (Kanban) and Job Search Research Queue (list) Deal views in CRM. Job Search stages are isolated from sales stages through the JS: prefix.

**A real test-site install, migration, CRM frontend check, and backup/restore test remain required.** Static CI cannot replace this verification.

## Documentation

- [Frappe 16 compatibility](docs/compatibility.md)
- [Architecture](docs/architecture.md)
- [Workflow and approvals](docs/workflows.md)
- [Operator API](docs/api.md)
- [Deployment](docs/deployment.md)
- [Known limitations](docs/limitations.md)
- [Procedures](docs/procedures/README.md)
