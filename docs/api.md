# Operator API

Whitelisted methods are exposed at `POST /api/method/job_search.api.METHOD` with standard Frappe authentication and arguments. A success response is `{ "ok": true, "data": ... }`. Invalid actions throw Frappe exceptions and must not be bypassed using raw status writes. Use a named operator account; human decisions require the signed-in approver.

| Method | Purpose |
| --- | --- |
| `register_opportunity(employer, name?)` | Reuse or create an Opportunity for an Organization; no Job required on initial discovery |
| `register_job(employer, title, source_url?, description?, requisition_id?, location?, source_name?, opportunity?)` | Create/deduplicate an independent Job, prefer an existing Opportunity at its Organization, explicitly select one when the Organization has multiple, and optionally capture the complete original posting |
| `associate_job(opportunity, job)` | Link an existing Job to an Opportunity at the same Organization; idempotent, does not forbid multiple Opportunity links |
| `capture_posting(job, description, source_name, source_url?, posting_title?, requisition_id?, snapshot?, opportunity?)` | Save an immutable complete posting snapshot for a Job. Unchanged latest content is idempotent; changed content creates a revision. Opportunity must be related to the Job |
| `reject_job(job, reason)` / `reopen_job(job, reason)` | Independent Job rejection / reset to **Unknown** for re-verification; does not reject an Opportunity or claim the Job is active |
| `perform_opportunity_action(opportunity, action, rationale?, scope?, search?, offer_details?, activity?)` | Pursuit transition, research handoff, qualification, rejection, reopening, and optional Activity Log payload for applied/interview/accept actions. Rejection scopes: `search`, `opportunity`, `organization` |
| `transition_opportunity(opportunity, stage, reason?, decision?, exception?, override_decision?)` | Server-validated Opportunity stage transition; not an approval bypass |
| `set_search_membership(search, opportunity, override)` | Per-Search Opportunity `Include`, `Exclude`, or `Default` override |
| `get_search_results(search)` | Matching Opportunities with readable Organization and Job titles plus IDs and match reasons |
| `get_search_research_strategies(search)` | Full assigned strategy instructions sorted by effective priority |
| `add_research(..., opportunity?, organization?, job?, sources?, procedure_execution?)` | Record cited research and source evidence with appropriate scope |
| `start_procedure`, `complete_procedure_step`, `complete_procedure` | Versioned procedure execution linked to Opportunity or Organization |
| `authorize_decision`, `record_human_decision` | Real approver-only decisions (Pursue rationale optional; other decision rationales required) |
| `publish_human_review`, `request_human_review` | Opportunity research summaries and human review task |
| `record_application`, `record_interview`, `create_follow_up` | Opportunity-level submissions, interviews, and follow-ups |
| `get_opportunity_context`, `get_company_dossier` | Combined Opportunity/Job/Organization evidence and history |
| `get_work_queue`, `get_research_queue`, `get_follow_up_queue`, `get_human_action_queue` | Operating queues, keyed by Opportunity |
| `reopen_organization(organization, reason)` | Reverse an Organization-wide rejection explicitly; separate from reopening individual Opportunities |

**Example:**

```sh
curl -X POST https://SITE/api/method/job_search.api.register_job \
  -H 'Authorization: token API_KEY:API_SECRET' \
  -H 'Content-Type: application/json' \
  -d '{"employer":"Example Ltd","title":"Software Engineer","source_url":"https://example.org/careers/42","description":"Full original job description here"}'
```

`register_opportunity` creates the pursuit without claiming that a qualifying Job exists. New Opportunities cannot advance to Ready to Review until at least one linked Job is verified as Active and satisfies the selected active Job Search's requirements.

For source-specific Job updates, use the Job DocType and `capture_posting`. Human-facing research findings (`research_findings`), recommendation (`research_recommendation`), application materials for review (`application_materials_for_review`), interview preparation (`interview_preparation`), and human instructions (`human_feedback_and_instructions`) are Opportunity fields. The complete `job_description` and `research_heuristics` are Job fields. The deprecated `posting_digest` argument to `publish_human_review` is not accepted for new Opportunity writes; save a real Job Posting instead.

**Activity Log and stage changes:** Opportunity Activity rows have Date, required Type, optional Contact, Platform and Notes, displayed oldest first. Mark Applied requires the signed-in human approver and an **Application** activity, not a separate Authorize Application decision or detailed application record. Begin Interviewing requires an Interview activity and an interview record; Accept Offer requires an Acceptation activity plus offer details and the actual human Accept Offer decision. If the corresponding activity already exists, the action does not create a duplicate. Automatic **Rejection** activities (today's date and reason as Notes) occur for **Opportunity Globally** / **Entire Organization** rejection only, never Search Only or independent Job rejection.

**Rejection details:** Search-only rejection writes an Opportunity Exclude override on only that Search and **does not** move the shared Opportunity to Rejected. Opportunity-global rejection sets the Opportunity global flag and status; Organization rejection affects every Opportunity at that Organization. Job rejection only invalidates that Job. Reopening a rejected Opportunity does not automatically reopen its Organization or rejected Jobs.

Research Strategies are independent top-level `Research Strategy` documents. Every assigned strategy must be followed in effective-priority order as returned by `get_search_research_strategies`, independent of heuristic qualification claims.
