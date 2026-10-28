# Job status workflow

The Job has one user-facing **Status** field. The eight allowed values are **Discovered**, **Researching**, **Ready to Review**, **Qualified**, **Applied**, **Interviewing**, **Accepted**, and **Rejected**. There is no separate prefixed stage field. **Preparing**, **Screening**, **Offer**, **Withdrawn**, and **Closed** are legacy statuses, not current choices.

The normal progression is **Discovered → Researching → Ready to Review → Qualified → Applied → Interviewing → Accepted**. **Rejected** is a terminal outcome; not every rejection scope changes Job status.

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

The UI exposes **Mark Qualified** as the primary action in Ready to Review, **Needs Research** and **Reject** alongside it, then **Mark Applied**, **Begin Interviewing**, and **Accept Offer** as the respective primary actions. **Reject** is under **More Actions** outside Ready to Review. Human action buttons require the signed-in **Job Search Approver**; the operator API may transition stages only under the same server-side safeguards. Do not create or impersonate human decisions to advance a job.

**Reject From** options in the modal are **Search Only**, **Job Globally**, and **Entire Organization**:

- **Search Only** writes an explicit Exclude override on the selected search; the Job's status does not change.
- **Job Globally** sets the job's rejection flag and transitions its status to **Rejected**, except an already Accepted job retains its status.
- **Entire Organization** globally rejects the organization and hides its jobs from searches; the individual Job's status does not change.

The actual transition graph also permits **Accepted → Rejected** and **Rejected → Researching**; reopening a terminal job to Researching requires an authorized **Override** exception and a reason. Rejection rules and authorized exceptions are enforced server-side. Workflow history remains in immutable transition records. Prior schema migration maps **Preparing → Qualified**, **Screening → Applied**, **Offer → Interviewing**, and **Withdrawn / Closed → Rejected**; it does not discard historical records.

## Ready to Review: active search and heuristic requirements

A Job's **Active Job Search** in **Job Search Fields** chooses the search used for this gate. Directly after **Job Details**, the **Research Heuristics** child table shows one row per configured custom heuristic and one built-in **Job Title** heuristic when the active search has reference titles, with the heuristic's name, instructions, and editable **Value**. The name and instructions come from the search; the researcher fills in Value. Changing **Active Job Search** or using **More Actions → Sync Research Heuristics** synchronizes the rows. **Opening or refreshing a Job does not synchronize its heuristics or mark it edited.** Synchronization also runs before the Ready to Review action; save any changes it makes before transitioning. Values remain associated with their original heuristic IDs, even when rows are reordered; deleting answers for heuristics no longer present in the selected search requires confirmation. The child-table display uses separate **Heuristic** and **Value** columns. The Value column wraps long assessments and preserves line breaks; open a row to edit its Value. Save values before review.

To transition **Researching → Ready to Review**, the server requires all of the following:

1. **Active Job Search** is set and refers to an existing, enabled search.
2. The Job satisfies **every deterministic search filter**: complete location (case-insensitive), employment type, work arrangement, seniority, posted-on-or-after date, compensation period, and minimum compensation with required currency as applicable. An unconfigured filter imposes no condition. Missing dates and compensation do not satisfy configured minima.
3. Neither the Job nor its employer is globally rejected, and the Job is not explicitly **Excluded** from the active search. If the search has **Require Explicit Heuristic Approval** enabled, it also needs an explicit **Include** override.
4. There is **exactly one assessment row for every current search heuristic**, identified by its underlying row ID; each has a nonblank **Value**. Missing, blank, duplicate, and unrelated/stale heuristic entries block readiness.

Errors enumerate individual failed requirements, rather than simply indicating that the search does not match. Both the form action and `job_search.api.transition_opportunity(..., stage="Ready to Review")` use the same Job validation hook. Even an approved workflow exception **does not bypass readiness checks**. A search's explicit Include override can admit a nonmatching job to the *search results*, but **does not bypass deterministic checks for Ready to Review**.

Heuristic values are researcher assessments, not automatically verified findings. The built-in Job Title heuristic accepts a similar title or a matching role described in the posting; it is not an exact-title filter. Its description lists the search's reference titles. Recording a Value does not replace the separate **cited research**, **completed procedure**, or **human Pursue decision** required for Qualified. A researched but not-yet-approved opening remains **Researching** or **Ready to Review**, never automatically Qualified.
