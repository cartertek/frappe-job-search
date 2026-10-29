# Job status workflow

The Job has one user-facing **Status** field. The eight allowed values are **Discovered**, **Researching**, **Ready to Review**, **Qualified**, **Applied**, **Interviewing**, **Accepted**, and **Rejected**. There is no separate prefixed stage field. **Preparing**, **Screening**, **Offer**, **Withdrawn**, and **Closed** are legacy statuses, not current choices.

The normal progression is **Discovered → Researching → Ready to Review → Qualified → Applied → Interviewing → Accepted**. **Agents must resolve every in-progress research opportunity by either rejecting it or completing its research and moving it to Ready to Review.** Do not leave investigated, unsuitable opportunities indefinitely in Researching or send unsuitable opportunities for human review. **Rejected** is a terminal outcome; not every rejection scope changes Job status.

## Transitions and requirements

| From | Action / target | Requirements |
|---|---|---|
| Discovered | Agent transitions to Researching | Begin researching the specific opening; no human Pursue decision is required merely to research |
| Researching | **Ready to Review** | Active Job Search and every review-readiness check below must pass |
| Ready to Review | **Mark Qualified** → Qualified | Human **Pursue** decision with rationale; cited research and a completed `research-employer`, `research-opening`, or `qualify` procedure (unless a separately authorized workflow exception applies) |
| Ready to Review | **Needs Research** → Researching | Return for additional work, not a qualification or approval |
| Qualified | **Mark Applied** → Applied | Existing **Authorize Application** human decision; saved, confirmed application with submission date and identifiable resume, cover letter, or other materials |
| Applied | **Begin Interviewing** → Interviewing | At least one recorded interview |
| Interviewing | **Accept Offer** → Accepted | Offer details and an explicit human **Accept Offer** decision with rationale |
| Discovered / Researching / Ready to Review / Qualified / Applied / Interviewing | **Reject** | Scope and reason required; effects depend on selected scope |

The UI exposes **Mark Qualified** as the primary action in Ready to Review, **Needs Research** and **Reject** alongside it, then **Mark Applied**, **Begin Interviewing**, and **Accept Offer** as the respective primary actions. **Reject** is under **More Actions** outside Ready to Review. Agents with **Job Search Operator** permission may **Reject** opportunities during research, with a recorded rationale. Human approval is required for **Mark Qualified** and **Accept Offer**; agents must not create or impersonate human decisions.

**Reject From** options in the modal are **Search Only**, **Job Globally**, and **Entire Organization**:

- **Search Only** writes an explicit Exclude override on the selected search; sets the Job status to **Rejected** (unless already Accepted), without setting its global rejection flag.
- **Job Globally** sets the job's rejection flag and transitions its status to **Rejected**, except an already Accepted job retains its status.
- **Entire Organization** globally rejects the organization and hides its jobs from searches; the individual Job's status does not change.

Agent rejections preserve the signed-in agent’s rationale in the Job timeline; they do **not** create human approval decisions.

The actual transition graph also permits **Accepted → Rejected** and **Rejected → Researching**; reopening a terminal job to Researching requires an authorized **Override** exception and a reason. Rejection rules and authorized exceptions are enforced server-side. Workflow history remains in immutable transition records. Prior schema migration maps **Preparing → Qualified**, **Screening → Applied**, **Offer → Interviewing**, and **Withdrawn / Closed → Rejected**; it does not discard historical records.

## Ready to Review: active search and heuristic requirements

A Job's **Active Job Search** in **Job Search Fields** selects the search used for this gate. The **Heuristic Claims** table contains **Heuristic**, **Exact Quote**, **Reasoning**, **Source URL**, and **Source Date**. Researcher claims stay associated with the configured heuristic ID even when search heuristics are reordered. **Load Heuristic Choices** updates the available heuristic names without automatically editing or removing saved claims. Open a row to enter or edit its supporting evidence. More than one claim per heuristic is allowed; save and validate claims before requesting Ready to Review.

To transition **Researching → Ready to Review**, the server requires all of the following:

1. **Active Job Search** is set and refers to an existing, enabled search.
2. The Job satisfies **every deterministic search filter**: complete location (case-insensitive), employment type, work arrangement, seniority, posted-on-or-after date, compensation period, and minimum compensation with required currency as applicable, **only if a compensation minimum is provided**. When **Compensation Not Given** is checked, numeric compensation matching is skipped. An unconfigured filter imposes no condition. Missing dates do not satisfy configured date minima. Each Job must provide Compensation Min or check Compensation Not Given; with the latter checked and the search configured to Allow Heuristic, the built-in Minimum Compensation assessment is required for Ready to Review.
3. Neither the Job nor its employer is globally rejected, and the Job is not explicitly **Excluded** from the active search. If the search has **Require Explicit Heuristic Approval** enabled, it also needs an explicit **Include** override.
4. Every required search heuristic has **at least one valid claim** (duplicates are allowed). Each claim must use a configured heuristic ID/name, a nonblank **Exact Quote**, a valid **Source URL**, nonblank **Reasoning**, and **Source Date** of `YYYY-MM-DD` or `None`. If the search has **Posted On Or After**, every claim must have a real published date **on or after** that threshold; `None` or older dates do not count. Invalid or unrelated/stale claims block readiness even when other valid claims exist.

Errors enumerate individual failed requirements, rather than simply indicating that the search does not match. Both the form action and `job_search.api.transition_opportunity(..., stage="Ready to Review")` use the same Job validation hook. Even an approved workflow exception **does not bypass readiness checks**. A search's explicit Include override can admit a nonmatching job to the *search results*, but **does not bypass deterministic checks for Ready to Review**.

Heuristic reasoning is a researcher assessment, not independently verified by the server. The built-in Job Title heuristic accepts a similar title or a matching role described in the posting; it is not an exact-title filter. Its instructions list the search's reference titles. A claim does not replace the separate **cited research**, **completed procedure**, or **human Pursue decision** required for Qualified. A researched but not-yet-approved opening remains **Researching** or **Ready to Review**, never automatically Qualified.

## Semantic Job research fields

The **Job Details** section contains **Job Description** (`job_description`), storing the posting's description, not an abstract or digest. Research Notes fields are `research_findings`, `research_recommendation`, `application_materials_for_review`, `interview_preparation`, and `human_feedback_and_instructions`. These names are authoritative for agent reads and writes; migration copies content from the previous `*_digest`, `agent_recommendation`, `application_review`, `interview_brief`, and `human_feedback` fields without removing the historical columns.

## Heuristic claims and source evidence

In the Job form, each **Heuristic Claim** specifies a configured heuristic, an **Exact Quote** copied verbatim from the source (**not** paraphrased), **Reasoning** connecting the quote to the selected heuristic, a **Source URL** containing the quotation, and **Source Date**. Both Reasoning and Source Date are required. Source Date is a strictly validated calendar date (`YYYY-MM-DD`) or the exact text `None` only when the source has no publication date. Do not substitute the retrieval/check date for publication date. When the search sets **Posted On Or After**, a claim is eligible only when its real Source Date is on/after that threshold; `None` is allowed to be recorded but is **not eligible** for the review gate. When the search has no such threshold, `None` can be used. All saved claims must be complete and valid, and each required heuristic must have at least one qualifying claim. The conditional Minimum Compensation heuristic is required only when Compensation Not Given is checked.

**Upgrading existing claims:** the schema adds empty Reasoning and Source Date cells to previously saved quotations. It does not invent a publication date or rationale. Researchers must fill both fields and revalidate existing claims before editing those Job records or moving them to Ready to Review. An undated claim (`None`) cannot remain on a Job being advanced under a dated search: replace it with dated evidence, or preserve the undated material in Research Findings instead. Older free-text heuristic assessments remain in **Research Findings & Sources**; they are not automatically converted into supported claims.

## Rejection details and reopening

A Rejected Job shows **Rejection Scope**, **Rejected From Search** (for a search-only rejection), and **Rejection Reason** in the **Overview**. **Rejection Scope** and **Rejection Reason** are editable, and edits are recorded in the Job document history. Updating the descriptive scope does not automatically change the underlying search, Job, or organization exclusion; use the rejection and reopening actions to change the effective rejection. The original rejection and subsequent reopening are recorded in the Job timeline. **Reopen** is available on Rejected Jobs to an authorized Job Search Operator; it requires a reason and returns the Job to **Researching**, clearing the Job's global rejection flag and its own search-only Exclude override when applicable. It does not clear other unrelated exclusions. If the organization itself is globally rejected, resolve that organization rejection separately before reopening the Job; reopening one Job must not reinstate all jobs of its organization.
