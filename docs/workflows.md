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

All transitions run through Frappe server hooks. Stage history and signed human decisions are retained. Creating an application, interview, or offer never automatically creates a human approval.

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

Rejecting a Job automatically records one **Rejection** activity on each associated Opportunity, dated today, with the rejection reason in **Notes** (no prompt and no Contact/Platform values). Opportunity rejections, including Search-only exclusions, follow the same rule. If the Opportunity already contains a Rejection activity, no additional Rejection row is generated. The independently rejected Job retains its own availability status and reason; an Opportunity Search-only rejection does not globally reject the pursuit.

Manually created Activity Log rows start with **Type blank** and require an explicit Type selection. The Activity Log displays in **Date ascending** order (oldest first), and this order is preserved on saving, including updates made through the API.
