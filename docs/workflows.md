# Opportunity pursuit and Job availability

The **Opportunity** owns the pursuit lifecycle. The **Job** owns only job-specific evidence, independent rejection and availability; the **Posting** retains its own snapshot status. These are separate and must not be conflated.

## Opportunity stage transitions

| From | Action / next status | Requirements |
| --- | --- | --- |
| Discovered | Begin Research → Researching | Operator begins investigating the Organization/hiring effort |
| Researching | Ready to Review | A configured, enabled Active Job Search and **at least one currently valid linked Job** pass all evidence and search requirements; cited Opportunity research and a completed research/qualification procedure are also required before handoff |
| Ready to Review | Mark Qualified → Qualified | Signed-in human Pursue decision (rationale optional); no additional Job, research, procedure, or eligibility checks at this stage |
| Ready to Review | Needs Research → Researching | Further evidence needed; no human decision fabricated |
| Qualified | Mark Applied → Applied | Signed-in human approver and a dated Application Activity Log row; no separate authorization or detailed submission record required |
| Applied | Begin Interviewing → Interviewing | At least one Opportunity-level interview record |
| Interviewing | Accept Offer → Accepted | Offer details and human Accept Offer decision |
| Active stages | Reject with scope | Operator must record rationale and choose Search Only, Opportunity Globally or Entire Organization |
| Rejected | Reopen → Researching | Operator reason; does not undo Organization rejection or unrelated Search exclusions |

All transitions run through Frappe server hooks. Stage history and signed human decisions are retained. Creating an application, interview, or offer never automatically creates a human approval. **Qualified** is strictly the signed-in human's Pursue decision and does not recheck research or eligibility after Ready to Review.

## Ready-to-Review qualification

An Opportunity uses its **Active Job Search** (`active_job_search`) to evaluate its associated Jobs. It must have at least one Job meeting **all** of that Search's deterministic filters and the required heuristic-claim evidence, while the Search and Organization/Opportunity remain eligible. A Job with `Closed`, `Rejected`, or `Unknown` availability is **not confirmed Active** and cannot qualify.

Each linked Job retains its **Job Description** (full original source body), **Job Posting** history, identity/requisition, geography, work arrangement, employment type, seniority, compensation, evidenced Last Active Date and dated source, and **Heuristic Claims** table. Each required claim has the exact quote, source URL, reasoning, and a real source publication date `YYYY-MM-DD` (or literal `None` when no publication date exists). If the Search has an Active In the Past cutoff, evidence must meet it; an undated claim cannot meet a dated cutoff. The server checks completeness and dates, not the truth of the claim; agents must research and verify the underlying facts.

**An Include override can admit a candidate to search results despite deterministic mismatches; it cannot bypass Ready-to-Review qualification.** Other Jobs may support the same Opportunity even if one Job becomes invalid. A Job change triggers an eligibility recheck; if an Opportunity in Ready to Review loses its last valid Job it returns to Researching. Later historical pursuit stages and their approvals are preserved while the Opportunity displays Needs Research.

## Rejection and reopening

- **Search Only:** excludes this **Opportunity** from one Search using the Search's `Job Search Membership` row. Does **not** globally reject or close the Opportunity; other Searches may still match it. Clearing the exclusion requires an explicit operator action with reason.
- **Opportunity Globally:** sets the global rejection flag on that Opportunity and moves its pursuit to Rejected, subject to preserving an already Accepted historical outcome.
- **Entire Organization:** rejects the Organization globally and disqualifies all its Opportunities. Clearing the Organization's flag is a separate, reasoned action; it does not silently reopen Opportunities.
- **Job-only rejection:** changes Job availability to Rejected and records a reason. This is not any of the above Opportunity scopes. Reopening resets its availability to Unknown for a new verification, rather than asserting it is Active.

Review records, original postings, comments, decisions, assignments, task history and signed-in author attribution are retained; agents never impersonate the user or Administrator.

## Opportunity Activity Log (issue #18)

Every Opportunity includes an editable **Activity Log** child table with **Date**, **Type**, **Contact**, **Platform**, and **Notes**. Date defaults to the current day, and Type is one of **Message, Application, Interview, Offer, Rejection, Acceptation, Note**. Contact, Platform and Notes are optional. These entries track the actual communication and pursuit history alongside (not in place of) the existing detailed application/interview/approval records.

Before **Mark Applied**, **Begin Interviewing**, or **Accept Offer**, the system checks for a matching Activity Log row (respectively **Application**, **Interview**, **Acceptation**). If no row exists, the form prompts for Date (default today), optional Contact, Platform and Notes; the matching Type is set automatically. The new activity and stage transition are saved together. If the required row already exists, there is no extra activity prompt. For Accept Offer, the existing offer details and human-approval rationale dialog is retained, and the activity fields are included only when Acceptation is missing. Direct REST/ORM status transitions enforce the same activity requirement.

Mark Applied requires the actual human approver and a dated Application activity, not a separate approval or detailed submission record. Optional detailed application records remain available. Begin Interviewing still requires the existing interview record, and Accept Offer retains its human acceptance and offer-details requirements.

## Rejection activities and log order

Rejecting an **Opportunity Globally** or **Entire Organization** automatically records one **Rejection** activity, dated today, with the rejection reason in **Notes** (no prompt and no Contact/Platform values). If the Opportunity already contains a Rejection activity, no additional row is generated. **Rejecting an individual Job does not add an Opportunity activity** and only changes that Job’s own availability and rejection reason. A **Search Only** exclusion does not add a Rejection activity or globally reject the pursuit.

Manually created Activity Log rows start with **Type blank** and require an explicit Type selection. The Activity Log displays in **Date ascending** order (oldest first), and this order is preserved on saving, including updates made through the API.

## Derived Applied field (issue #25)

**Opportunity.Applied** (`applied`) is a read-only, indexed, filterable Check field computed from the **Activity Log**, **not** from pursuit Status or the separate Applied On date. It is **true if and only if at least one Activity row has Type = Application**; otherwise it is false, including for historically Applied Opportunities lacking an Application activity. It remains true after later stage transitions (Interviewing, Accepted, etc.) as long as an Application activity exists. Removing or changing the last Application activity makes it false; adding a new Application activity makes it true. Normal form saves and database-level Activity insert/update/delete operations synchronize the stored value in the same transaction, so standard list filters, reports and searches see the current result without a background refresh. The field is not manually editable. Existing Opportunities are backfilled during `bench migrate`.

## Derived Applied On and Common Contact

**Applied On** (`applied_on`) is a read-only, indexed Date field showing the **latest Date among Application Activity Log entries**. It is blank if there are no Application activities, even if the Opportunity's pursuit Status is Applied or a separate historical application record exists. It can be displayed, sorted (ascending or descending), and filtered using the standard Opportunity list. Changing an Application activity's date, type, parent Opportunity, or deleting the final Application activity updates or clears Applied On immediately. Never edit the derived value directly.

**Common Contact** (`common_contact`) is a read-only, indexed Data field containing the **most frequent non-empty Contact** in the Opportunity's Activity Log, across all activity types. Leading and trailing whitespace is ignored; blank contacts are excluded. Ties between equally common contacts resolve alphabetically for a repeatable result. The field clears when there are no non-empty Contact values. Both fields are synchronized on ordinary Frappe saves and direct child Activity insert, update, move or deletion, with no scheduled job or refresh required.
