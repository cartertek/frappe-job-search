# CRM UI integration audit — 2026-10-17

Scope: independently compare the Job Search app's shipped hooks, fixtures, APIs and DocTypes to Frappe CRM **1.88.0** Vue page implementation. This identifies *UI integration gaps*, not proof of backend failures. CRM must remain the sole end-user UI; do not restore a separate Frappe Desk app.

## Fixed and verified on `jobsearch.localhost`

- Deal Quick Entry (`CRM Fields Layout`, `Quick Entry`): 10 job fields in the existing Create Deal form. Existing CRM fields retained.
- Deal's **Data** tab (`CRM Fields Layout`, `Data Fields`): 23 job fields, including job metadata, compensation, research decision and stage. Live `get_fields_layout` endpoint checked.
- Deal's **left side panel** (`CRM Fields Layout`, `Side Panel`): 9 summary fields including job title, stage and next action. Live `get_sidepanel_sections` endpoint checked.
- Job Search Pipeline and Research Queue are scoped saved views on CRM Deals; code seeds these via after_migrate.
- Layout additions are idempotent: append only missing fields; do not overwrite existing user-defined tabs/sections.

## Unimplemented / unverified CRM UI paths

| Priority | Area | Current implementation | Needed CRM-native UX and test |
| --- | --- | --- | --- |
| P0 | Job opportunity creation / stages | Job-specific Deal fields and server validation exist | Test create from CRM as operator (not Administrator), initial `JS: Discovered`, edits and Kanban transitions; check ordinary Deal unchanged and invalid transitions blocked |
| P0 | Job description / source preservation | `Job Search Posting` and `Job Search Source` DocTypes, capture API, revision linking | CRM Deal should display linked posting, archived description, sources and posting history. Create Deal fields currently collect only URL, not original text; creating a Deal alone does not call posting capture API |
| P0 | Research and citations | `Job Search Research` / source child records; API to add research | No shipped CRM Deal component for creating, browsing, verifying or rechecking research and citations |
| P0 | Procedure executions | Versioned procedure DocTypes and start/step/complete API | No shipped CRM Deal UI to choose, execute, complete and inspect procedures |
| P0 | Human approvals | `Job Search Decision` DocType, approver-only API, transition checks | No shipped CRM-native approval prompt/action, decision audit panel or separate approver workflow |
| P0 | Applications | Submission record, prior authorization check, stage enforcement | No shipped CRM-native application preparation, submission confirmation, material/revision and authorization UI. External submission remains manual |
| P1 | Interviews / offers | Interview record API; offer details on Deal | No shipped CRM-native interview rounds, scheduling/contact view or offer decision flow |
| P1 | Tasks and work queues | CRM Task automation and queue read APIs | Standard CRM tasks work; no shipped special follow-up queue/aging or research-freshness queue interface |
| P1 | Company research | `js_*` CRM Organization fields and company dossier API | Employer's custom fields not yet added to CRM's Organization Quick Entry/Data/Side Panel layouts; no dossier UI |
| P1 | Evidence/transition review | Transition records and immutable snapshots | No Deal-level timeline for Job Search events/revisions beyond native CRM activity |
| P1 | Roles and access | Operator/Approver roles plus native CRM permissions | Integration tests needed for CRM UI and all whitelisted methods with operator, approver and unauthorized accounts |
| P2 | Reporting | Work queue and dossier JSON APIs | No dedicated CRM saved views for stale research, waiting decisions, deadlines or procedure progress; initial Research Queue view only filters by stage |

## Design and test direction

- Prefer CRM Fields Layout and existing CRM Deal/Organization views where that genuinely covers a field/edit interaction.
- For related records and procedures, extend CRM Deal's existing pages/tabs through supported CRM extension points or an intentionally maintained extension to the existing CRM frontend. Do **not** present a separate Desk app or call an API-only flow finished.
- Test against Frappe 16.52.0 / CRM 1.88.0 in a disposable site with a non-admin operator and separate approver. Verify install, migration idempotency, mobile Deal layout, denial behavior, task idempotency, posting revisions and backup/restore.
- Treat the complete original implementation specification as the acceptance criteria; this audit is a list of observed gaps, not a replacement for the spec.
