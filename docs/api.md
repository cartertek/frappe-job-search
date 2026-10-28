# Operator API

Each method is exposed as POST to /api/method/job_search.api.METHOD (or the Frappe method request convention). Pass JSON/form arguments in the usual Frappe manner. Success returns an ok=true envelope with data. Validation failures use Frappe exceptions and standard rollback semantics; some errors are not converted to a structured error envelope.

| Method | Description |
| --- | --- |
| register_opportunity | Register employer, Job Search Opportunity, and saved posting/discovery source; deduplicate exact URL or strict role match |
| capture_posting | Record a full posting snapshot; unchanged content is idempotent, changed content produces a new immutable revision |
| add_research | Add source-backed research and optionally create linked source records |
| start_procedure | Start a specific active procedure version against a Job or employer |
| complete_procedure_step | Complete one execution step and record findings |
| complete_procedure | Complete after required steps and assessment |
| authorize_decision | Human approver-only authorization: Pursue, Authorize Application, Accept Offer, Withdraw, Override (only when appropriate; never auto-issue on the operator's behalf) |
| perform_job_action | Agents with Job Search Operator permission may reject opportunities with a rationale and scope, or move researched opportunities to Ready to Review. Reject does not issue a human Decision record. Pursue and Accept Offer still require a signed-in approver |
| transition_opportunity | Validated Job stage change; Ready to Review requires a matching active search and all heuristic values, Qualified requires human Pursue approval and cited completed research; later stages require corresponding authorizations and records |
| record_application | Record a confirmed external submission, checking prior approval and materials |
| record_interview | Record interview round, schedule and Frappe Contacts |
| create_follow_up | Add linked Job Search Task |
| get_work_queue | Query opportunities, incomplete executions, and active linked Job Search tasks |
| get_follow_up_queue | Group open Job Search Tasks as overdue, upcoming, later or unscheduled (optional horizon_days default 14; argument `horizon`) |
| get_research_queue | Query opportunities with missing/unverified/stale research (optional `stale_after_days`, default 90) |
| get_company_dossier | Employer, opportunities, postings, research and sources |
| get_opportunity_context | Read the Job/employer dossier and linked records |

Frappe native REST resource endpoints remain appropriate for routine record CRUD. All operations should run under a dedicated, named operator user with Job Search Operator permissions, never as Administrator.

Example:

    curl -X POST https://SITE/api/method/job_search.api.register_opportunity \
      -H "Authorization: token API_KEY:API_SECRET" \
      -H "Content-Type: application/json" \
      -d '{"employer":"Example Ltd","title":"Software Engineer","source_url":"https://example.org/careers/42","description":"Full original posting text"}'

Idempotency: re-registering an identical posting URL returns its opportunity; strict employer + requisition + title + location may reuse a Job; weaker matches are flagged. Submitted application reference is unique within a Job. If posting content changes at the same URL, the registration/capture API records a new snapshot linked to its predecessor. The old snapshot cannot be edited in-place. Reverting to an earlier description creates another observation in the history.

### Semantic Job fields and review API

Use the native **Job Description** (`job_description`), **Research Findings & Sources** (`research_findings`), **Agent Recommendation** (`research_recommendation`), **Application Materials for Review** (`application_materials_for_review`), **Interview Preparation** (`interview_preparation`), and **Human Feedback / Instructions** (`human_feedback_and_instructions`) fields in Job records. The `publish_human_review` endpoint accepts the matching semantic argument names; its previous `posting_digest`, `research_digest`, `recommendation`, `application_review`, and `interview_brief` arguments remain accepted for backward compatibility. Do not use the old column names for new records or direct Frappe field writes.
