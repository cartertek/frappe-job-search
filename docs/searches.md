# Job Search collections and searches

`Job Search Opportunity` (jobs) and `Job Search Employer` (organizations) are independent collections. The `Job Search Search` collection consists of named reusable searches over jobs; a search never owns or duplicates a job or organization.

## Deterministic filters

Each search may filter deterministically by location text, employment type, work arrangement, seniority, posting date, and minimum compensation (with currency/period for comparable values). Empty filters impose no condition. Location uses case-insensitive full-field equality; enumerated fields use exact matching. A missing posted date does not match a configured date. When a job has stated compensation, its minimum is compared with the search minimum if present. Checking **Compensation Not Given** bypasses the numeric compensation filter; research heuristics may then assess expected pay. A currency is considered only when a compensation minimum is set, avoiding Frappe's implicit default currency accidentally filtering the collection.

By default, all non-rejected jobs matching these filters appear in the search. Changes to jobs or filters immediately affect results without a separate synchronization step.

## Subjective heuristics

`Custom Research Heuristics` is the child table on each search. The separate **Job Titles to Match** field defines a built-in **Job Title** research heuristic, not an exact-title filter. Its generated instructions explain that a job title should resemble one of the listed titles and/or its posting description should describe a matching role; the titles are included in that instruction. A Job Title row appears on the Job assessment table when at least one reference title is supplied. Each row has a required **Name** and **Description**, recording an individual subjective criterion for the researching agent. The application does **not** pretend to evaluate those instructions deterministically. When `Require Explicit Heuristic Approval` is enabled, only jobs explicitly added via an **Include** override appear in the search. The agent must evaluate the instructions and explicitly include jobs using the API or the Overrides table. The Job form has an **Active Job Search** link and a **Heuristic Claims** child table. Each claim requires its configured heuristic, an exact verbatim quote, and a URL to the source containing that quote. Multiple claims per heuristic are allowed; at least one sourced claim per required heuristic is necessary for Ready to Review. See [Job workflow](workflows.md) for the stricter transition checks.

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

Current Job statuses are **Discovered, Researching, Ready to Review, Qualified, Applied, Interviewing, Accepted, Rejected**. Search membership is independent of these statuses: using **Reject → Search Only** marks the Job **Rejected** and excludes it from the selected search, without setting the global rejection flag. **Ready to Review**, however, requires a matching active search and completed heuristic values; an Include override cannot bypass its deterministic checks. See [Job status workflow](workflows.md).

## Compensation without a published amount

The Job form requires either **Compensation Min** or **Compensation Not Given**. Checking **Compensation Not Given** clears and disables Compensation Min, Compensation Max, Currency, and Compensation Period. A search may enable **Allow Heuristic** under **Minimum Compensation**. When enabled and a minimum is configured, a built-in **Minimum Compensation** research heuristic asks the researcher to determine, using the company size, role and market, whether expected compensation is well above the stated minimum. The instructions include that minimum. The heuristic is **required at Ready to Review only when Compensation Not Given is checked**; it is optional when actual compensation is supplied.
