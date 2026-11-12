# Frappe Job Search

A **standalone Frappe v16 application** for researching and tracking job opportunities, applications, interviews, approvals, and follow-ups. **Frappe CRM is not required.** The human interface is the standard Frappe Desk **Job Search** Workspace, app-owned DocType forms and list views. Agents use permission-checked API methods.

## Data model

- **Organization** (`Job Search Employer`) — independent employer identity, research and global rejection.
- **Job** (`Job`) — independent specific position: original description and posting history, location, compensation, recency, heuristic evidence, and a separate **Availability** (`Unknown`, `Active`, `Closed`, or `Rejected`). Rejecting a Job invalidates only that position.
- **Opportunity** (`Opportunity`) — one hiring pursuit at an Organization, normally shared by its Jobs. A separate hiring team or division can warrant another Opportunity. Each Opportunity holds a **Jobs** child table; a Job can support more than one Opportunity. Opportunity owns the entire pursuit lifecycle (Discovered → Researching → Ready to Review → Qualified → Applied → Interviewing → Accepted, plus rejection), reviews, decisions, applications, interviews and offers.
- **Job Search Search** — reusable deterministic Job filters, source-backed heuristics, prioritized Research Strategies, and **Opportunity-specific** Include/Exclude overrides. One Opportunity can match more than one Search.
- **Job Search Posting, Source, Research, Procedure, Procedure Execution, Application, Interview, Decision, Transition, Task** — evidence and audit records. Posting is a separate, immutable Job-specific revision history; pursuit history belongs to Opportunity.

The Desk workspace and sidebar contain separate **Jobs** and **Opportunities** collections. Researching a Job can establish eligibility for its Opportunity, but it does not authorize a human Pursue decision. Agent research and rejection run as the signed-in operator; **human authorization is never impersonated**.

## Install on a new Frappe site

Requires stable Frappe `version-16` and Python 3.14. After fetching this app's `master` branch:

```sh
bench --site YOUR-SITE install-app job_search
bench --site YOUR-SITE migrate
```

Open `/desk` and the **Job Search** Workspace. Assign **Job Search Operator** to an agent and **Job Search Approver** to the human reviewer. Both may access the app-owned DocTypes; no CRM Sales role is necessary. Wiki is optional and deployed separately by the companion platform repository.

## Upgrading from the previous Job-as-Opportunity model (issue #15)

**Back up the site and verify the backup before changing app code or migrating.** The former `Job Search Opportunity` DocType held individual Jobs and their pursuit stages. The new migration preserves every existing Job name/ID by renaming that DocType to `Job`, creates one same-ID `Opportunity` per historical Job with a linking child row, and moves the pursuit status and associated records to that Opportunity. The guarded v6 reconciliation then merges **compatible historical duplicate Opportunities** into one Organization-named pursuit, while preserving the original Jobs and their identifiers and archiving the original pursuit histories. Distinct hiring teams or incompatible human decisions are **not** auto-merged. New Jobs normally reuse the Organization's existing Opportunity.

1. Validate the migration on a **separate copy of production data**. Record baseline Jobs, Organizations, Postings, Sources, Research, Decisions, Transitions, Tasks, Search Memberships, Comments, and Files.
2. Back up production again; deploy the full compatible app release (schema and patch together) and run `bench --site YOUR-SITE migrate`. The v5 patch runs before DocType synchronization; after migration the app backfills Opportunities, Job links, source/job references, and search membership links.
3. Verify **all historical Job IDs exist under `Job`** and still link to an Opportunity. The initial same-ID Opportunities are consolidated only where compatible; do **not** expect every old Job to have a final same-ID Opportunity. Confirm the **Opportunity Consolidation** archives and inspect migrated task, transition, decision, application, interview, research, source, posting, activity, tag, and Search-membership references, preserving historical author/timestamps and approvals. Use `job_search.opportunity_migration.verify_opportunity_migration`.
4. Repeat the migration once to confirm idempotency; run strict desktop integrity validation, build assets if required by the release, and validate Desk forms, Search results, Wiki research handbook, and actual operator workflows.
5. **Do not roll back only the container image** after a schema migration; restore the matching database and files from the verified backup if rollback is required.

The older `job_search.migration.migrate_from_crm` is for importing from an ancient CRM-backed installation; it is not the migration mechanism for issue #15. Follow the companion [`job_search_platform`](https://github.com/JoshuaCWebDeveloper/job_search_platform) operations runbook when deploying the container stack.

## Agent API

See [API reference](docs/api.md). Entry points live in `job_search.api`, including `register_opportunity`, `register_job`, `associate_job`, `capture_posting`, `add_research`, `start_procedure`, `complete_procedure_step`, `complete_procedure`, `publish_human_review`, `request_human_review`, `record_human_decision`, `transition_opportunity`, `record_application`, `record_interview`, and the work/research/human-action queues.

## Documentation

- [Searches, filters, heuristics and rejection rules](docs/searches.md)
- [Workflow stages and authorization](docs/workflows.md)
- [Architecture](docs/architecture.md)
- [Operator API](docs/api.md)
- [Deployment](docs/deployment.md)
- [Human acceptance tests](docs/human-acceptance.md)
- [Known limitations](docs/limitations.md)
