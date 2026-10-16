# Workflow

Primary Deal stages are Discovered, Researching, Qualified, Preparing, Applied, Screening, Interviewing, Offer, Accepted, Rejected, Withdrawn, and Closed. Rejection, withdrawal or closure can be reached directly from several active stages; no fictitious intermediate stages are created. Reopening a terminal stage requires a documented approved exception.

The corresponding native CRM Deal Status records are prefixed JS: to avoid confusing them with ordinary sales statuses. Both js_stage and native status stay synchronized by the CRM Deal validate hook.

Protected transitions:

- Into Qualified: the qualification is Pursue, rationale exists, a human Pursue decision exists, and cited research plus a completed research/qualification procedure are present. An approved Override with rationale can waive the process and evidence requirement, not the human decision.
- Into Applied: a prior Authorize Application decision and confirmed saved application including date and materials.
- Into Interviewing: a saved interview or screening record.
- Into Offer: offer details.
- Into Accepted: an Accept Offer decision.
- Into Withdrawn: a Withdraw decision.
- Into Closed: closure rationale.
- Terminal to Researching: an Override decision with documented exception and reason.

Procedure executions cannot complete unless every required step is completed and the assessment is present. Moving the CRM Deal does not complete procedures automatically. Decisions, transitions, postings, and application records are historical, retained artifacts.

Always use the Frappe document save path. Raw SQL and frappe.db.set_value bypass framework validation and are prohibited for changing workflow statuses.
