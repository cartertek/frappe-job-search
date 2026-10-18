# Frappe Job Search

A **standalone Frappe v16 application** for researching and tracking job opportunities, applications, interviews, approvals, and follow-ups. **Frappe CRM is not required.** The human interface is the standard Frappe Desk **Job Search** Workspace, app-owned DocType forms and list views. Agents use permission-checked API methods.

## Data model

- **Job Search Opportunity** — employer, job details, stage, decision/approval state, recommendation, posting and application summaries, and review links.
- **Job Search Employer** — employer identity, careers page and research details.
- **Job Search Task** — deadlines, assignees, follow-ups, and review tasks.
- **Job Search Posting, Source, Research, Procedure, Procedure Execution, Application, Interview, Decision, Transition** — source evidence and immutable historical records.
- Built-in Frappe Users, Contacts, Comments, ToDos and file attachments are reused where appropriate.

A signed-in human with **Job Search Approver** authority uses the **Record Decision** button on a pending opportunity to open a one-time modal. Recording a `Decline` decision automatically closes the opportunity; other decisions are retained for agent-controlled stage transitions. Agents cannot impersonate approvers or submit external applications automatically.

## Install on a new Frappe site

Requires stable Frappe `version-16` and Python 3.14. After fetching this app's `master` branch:

```sh
bench --site YOUR-SITE install-app job_search
bench --site YOUR-SITE migrate
```

Open `/desk` and the **Job Search** Workspace. Assign **Job Search Operator** to an agent and **Job Search Approver** to the human reviewer. Both may access the app-owned DocTypes; no CRM Sales role is necessary. Wiki is optional and deployed separately by the companion platform repository.

## Upgrading an existing CRM-backed Job Search site

**Never uninstall CRM before migrating the Job Search data.** The old system stores opportunities in CRM Deal, employers in CRM Organization and tasks in CRM Task.

1. Back up the database and public/private files, and verify the backup is accessible outside the container.
2. While the existing CRM-containing image is still running, update the app code to this standalone release and run `bench --site YOUR-SITE migrate`. CRM remains installed during this step.
3. Preview with `bench --site YOUR-SITE execute job_search.migration.migrate_from_crm`.
4. Import historical records with `bench --site YOUR-SITE execute job_search.migration.migrate_from_crm --kwargs '{"confirm": True}'`. The operation is repeatable and preserves historical identifiers, timestamps and related activity links.
5. Validate all opportunities, employers, tasks, posting/research history, approvals, and attachments in Job Search Workspace.
6. Only after validation and once the CRM-free image is available, run `bench --site YOUR-SITE uninstall-app crm`, deploy the new image and migrate again.

See the companion [`job_search_platform`](https://github.com/JoshuaCWebDeveloper/job_search_platform) repository's cutover runbook. Rolling back an image **does not** roll back schema changes; retain the original backup.

## Agent API

See [API reference](docs/api.md). Entry points live in `job_search.api`, including `register_opportunity`, `capture_posting`, `add_research`, `start_procedure`, `complete_procedure_step`, `complete_procedure`, `publish_human_review`, `request_human_review`, `record_human_decision`, `transition_opportunity`, `record_application`, `record_interview`, and the work/research/human-action queues.

## Documentation

- [Workflow stages and authorization](docs/workflows.md)
- [Architecture](docs/architecture.md)
- [Operator API](docs/api.md)
- [Deployment](docs/deployment.md)
- [Human acceptance tests](docs/human-acceptance.md)
- [Known limitations](docs/limitations.md)
