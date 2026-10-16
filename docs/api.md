# Operator API

Each method is exposed as POST to /api/method/job_search.api.METHOD (or the Frappe method request convention). Pass JSON/form arguments in the usual Frappe manner. Success returns an ok=true envelope with data. Validation failures use Frappe exceptions and standard rollback semantics; some errors are not converted to a structured error envelope.

| Method | Description |
| --- | --- |
| register_opportunity | Register employer, CRM Deal, and saved posting/discovery source; deduplicate exact URL or strict role match |
| add_research | Add source-backed research and optionally create linked source records |
| start_procedure | Start a specific active procedure version against a Deal or employer |
| complete_procedure_step | Complete one execution step and record findings |
| complete_procedure | Complete after required steps and assessment |
| authorize_decision | Human approver-only authorization: Pursue, Authorize Application, Accept Offer, Withdraw, Override |
| transition_opportunity | Validated CRM Deal stage change with optional prior decision and exception |
| record_application | Record a confirmed external submission, checking prior approval and materials |
| record_interview | Record interview round, schedule and Frappe Contacts |
| create_follow_up | Add linked CRM Task |
| get_work_queue | Query opportunities, incomplete executions, and active linked CRM tasks |
| get_opportunity_context | Read the Deal/employer dossier and linked records |

Frappe native REST resource endpoints remain appropriate for routine record CRUD. All operations should run under a dedicated, named operator user with Job Search Operator and CRM permissions, never as Administrator.

Example:

    curl -X POST https://SITE/api/method/job_search.api.register_opportunity \
      -H "Authorization: token API_KEY:API_SECRET" \
      -H "Content-Type: application/json" \
      -d '{"employer":"Example Ltd","title":"Software Engineer","source_url":"https://example.org/careers/42","description":"Full original posting text"}'

Idempotency: re-registering an identical posting URL returns its opportunity; strict employer + requisition + title + location may reuse a Deal; weaker matches are flagged. Submitted application reference is unique within a Deal. A changed posting at the same URL must be captured as a separate snapshot through the native Posting record API.
