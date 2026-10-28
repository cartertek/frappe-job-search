# Job Search collections and searches

`Job Search Opportunity` (jobs) and `Job Search Employer` (organizations) are independent collections. The `Job Search Search` collection consists of named reusable searches over jobs; a search never owns or duplicates a job or organization.

## Deterministic filters

Each search may filter by job title text, location text, employment type, work arrangement, seniority, posting date, and minimum compensation (with currency/period for comparable values). Empty filters impose no condition. Job title (any complete line of the configured title list) and location use case-insensitive full-field equality; enumerated fields use exact matching. A missing posted date or salary does not match a configured date or compensation minimum. A currency is considered only when a compensation minimum is set, avoiding Frappe's implicit default currency accidentally filtering the collection.

By default, all non-rejected jobs matching these filters appear in the search. Changes to jobs or filters immediately affect results without a separate synchronization step.

## Subjective heuristics

`Research Heuristics` is a child table on each search. Each row has a required **Name** and **Description**, recording an individual subjective criterion for the researching agent. The application does **not** pretend to evaluate those instructions deterministically. When `Require Explicit Heuristic Approval` is enabled, only jobs explicitly added via an **Include** override appear in the search. The agent must evaluate the instructions and explicitly include jobs using the API or the Overrides table. The Job form also has an **Active Job Search** link and its own **Research Heuristics** child table for recording a value per heuristic; these answers are required before advancing to **Ready to Review**. See [Job workflow](workflows.md) for the stricter transition checks.

## Override and rejection precedence

1. **Reject organization globally:** none of its jobs appear in any search, even when explicitly included.
2. **Reject job globally:** it appears in no search, even when explicitly included.
3. **Exclude in this search:** the job never appears in this particular search.
4. **Include in this search:** the job appears regardless of deterministic filters and regardless of the `Require Explicit Heuristic Approval` setting, unless globally rejected.
5. **Default/no override:** matching deterministic filters cause inclusion, but only if explicit heuristic approval is not required.

An override is stored on the search as a `Job Search Membership` child record; `Default` removes it. Only one override per search+job is allowed. Global rejection is stored on the underlying job or employer. These actions do not modify other search filters or delete records.

## Desk UI and API

Open `/desk/job-search` → **Job Search Search**. Set search filters and researcher heuristics, save, then use **View Matching Jobs** to see results. **Remove** next to a result explicitly excludes it from that search. The search form's **Explicit Job Overrides** table supports manual inclusion and exclusion for any job, including jobs that do not meet the deterministic filters. The job and organization forms provide **Reject Job Globally** and **Reject Organization Globally** actions.

Agent endpoints in `job_search.api`:

- `get_search_results(search)` — matching non-rejected jobs and match reason.
- `set_search_membership(search, job, override)` — `Include`, `Exclude`, or `Default`.
- `reject_job(job)` — permanently sets the global rejection flag (it can be reversed by a properly authorized human editing the record).
- `reject_organization(organization)` — globally rejects the employer and thus all its jobs.

Current Job statuses are **Discovered, Researching, Ready to Review, Qualified, Applied, Interviewing, Accepted, Rejected**. Search membership is independent of these statuses: excluding a job from one search does not close or globally reject it. **Ready to Review**, however, requires a matching active search and completed heuristic values; an Include override cannot bypass its deterministic checks. See [Job status workflow](workflows.md).
