# Standalone architecture

The application runs on Frappe v16 without Frappe CRM. Frappe Users, Contacts, Files, Comments and ToDos remain available. The app owns these separate concepts:

- **Organization** (`Job Search Employer`): reusable employer identity, facts, and organization-wide rejection.
- **Job** (`Job`): the specific position, compensation/location/type/recency, original description, posted snapshots, heuristic claims, and independent availability (`Unknown`, `Active`, `Closed`, `Rejected`). Job rejection disqualifies only that position.
- **Opportunity** (`Opportunity`): one organization's hiring pursuit, normally one per Organization. Distinct divisions/hiring teams may have separate Opportunities. Contains a child table of **Opportunity Job** links, allowing multiple Jobs and permitting a Job to support multiple Opportunities. Owns all research/pursuit stage transitions, approvals, overall research summaries, rejection, applications, interviews, offers, and follow-ups.
- **Job Search Search**: reusable criteria and assigned Research Strategies. A Search discovers matching Opportunities through their associated Jobs. A single Opportunity can match several Searches; per-search overrides are keyed by Opportunity, not Job.
- **Posting**, **Source**, and **Research**: retain the existing historical records. Individual Postings are attached to the Job and optionally its Opportunity. Sources and Research may link to the Job when job-specific, the Opportunity when pursuit-specific, or the Organization when broadly applicable.

The Desk Job Search workspace includes separate **Opportunities**, **Jobs**, **Organizations**, and **Searches** collections. Agents use `job_search.api`; server-side hooks enforce stage transitions, role authorization, and evidence requirements on normal ORM/REST operations. Operators may investigate and reject, but **only the actual signed-in human approver** may authorize a Pursue/Apply/Accept decision. The application does not impersonate any user.

## Lifecycle boundaries

- **Opportunity:** Discovered → Researching → Ready to Review → Qualified → Applied → Interviewing → Accepted, with scoped rejection and reopening.
- **Job:** Unknown / Active / Closed / Rejected availability and independent Job rejection. Changing a Job triggers re-evaluation of its associated Opportunities without deleting historical decisions or activity.
- **Posting:** Its own observation-level status and immutable revisions; neither the Job nor Opportunity pursuit status is inferred from the mere existence of a posting.

The legacy `Job Search Opportunity` DocType represented individual Jobs. The version-5 migration renames that DocType and its SQL table to `Job`, creates a same-ID Opportunity for every existing Job, and attaches it with an `Opportunity Job` child record. This conservatively preserves distinct historical pursuits instead of automatically merging different approval or rejection histories. New Jobs normally reuse the existing Opportunity at their Organization, but can explicitly join another distinct hiring team or more than one Opportunity. Read [deployment](deployment.md) for the data-preservation and recovery contract.
