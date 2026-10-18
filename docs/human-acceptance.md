# Frappe CRM Job Search — human acceptance test

Current deployment checked: Frappe 16.52.0 / CRM 1.88.0 / `jobsearch.localhost`.

## Roles

- Agent: **Job Search Operator** plus CRM **Sales User** (or the appropriate CRM role). The agent uses the Job Search API and CRM document REST services, not a separate Job Search UI.
- Human: **Job Search Approver** plus CRM **Sales User**. A human review request automatically assigns the Deal using native Frappe `ToDo` assignment so the assigned human can open and edit that specific Deal.
- Administrative role is **not** required for either normal path. Agents cannot issue a signed human decision.

## Human tests in Frappe CRM

1. Open **Deals → Job Search Pipeline → an opportunity**. In the **Data** tab, check Job Opportunity fields: job title, source URL, full captured posting when available, latest posting revision, research findings, recommendation, application review, interview brief, and human feedback. The left sidebar contains the job summary and pending review status. Agents populate summaries through `publish_human_review`; records without agent research can legitimately show empty fields.
2. Open **Organizations** and an employer. Its Data tab and side panel expose careers site, category, priority, research status/date and employment notes.
3. With a pending review requested by an agent, use **Deals → Job Search Human Review** or the assigned **CRM Task**. Open the Deal, inspect supporting review material, select a choice in **Record Human Decision**, enter a **Decision Rationale**, and click **Save**.
4. Refresh the Deal. **Human Review Status** should be **Completed**, the transient decision/rationale inputs should be empty, **Last Human Decision** should identify the action/actor/time, and the assigned CRM Task should be **Done**. Original decision is persisted as an immutable Job Search Decision record.
5. Try an action outside the pending review type (for example, Accept Offer on a Pursue/Decline request). The save must fail. An operator account must not be able to record any human decision.
6. Agents can proceed via stage transition API only when stage-specific requirements are met. Moving to Qualified requires source-backed research, completed procedure, qualification + rationale, and a Pursue decision. Applied requires authorization and a saved confirmed application. Interviewing needs an interview record; Accepted needs Accept Offer approval.
7. For application reviews, confirm the agent's prepared materials are listed under **Application Materials for Review**. Actual external submission is manual and separate from approval. After confirmed submission, the Deal should show latest application link and submission date. Interview scheduling is displayed as a summary in the Deal.
8. Verify an ordinary CRM Deal with Job Search Opportunity unchecked remains an ordinary Deal and is excluded from the Job Search saved views.

## Automated/runtime checks already executed

- Backend site migration and multiple repeat migrations succeeded; CRM Quick Entry, Data and Side Panel layout endpoints returned the expected custom fields. The CRM frontend responded HTTP 200.
- Transaction-rolled-back live smoke checks of a complete stage sequence: Discovered → Researching → Qualified → Preparing → Applied → Interviewing → Offer → Accepted, including research, procedures, decisions, tasks, application and interview records, and seven transitions.
- Signed approver test: immutable Decision creation, transient form fields cleared, human-review task marked Done, human queue removed the completed request; mismatched pending decisions rejected.
- Separate temporary Sales User + Operator account: Deal access through native assignment, research-stage transition, task and transition actor attribution, review publication and posting capture succeeded. Unsupported qualification rejected.
- Separate temporary Sales User + Approver account: assigned Deal read/write permitted and its own signed approval succeeded, while the operator role could not approve.
- All temporary test data were explicitly rolled back. No external job applications or emails were submitted.

## Still required before production readiness

- Human browser acceptance for actual field rendering, interaction, task links, and the mobile CRM experience (API metadata checks do not constitute browser tests).
- Clean-site installation and upgrade/migration regression tests beyond the existing hotfixed stack; real automated Frappe/MariaDB tests in CI and backup/restore verification.
- Further UX refinement if human acceptance reveals insufficient context or review ergonomics; advanced analytics and notifications are deferred.
