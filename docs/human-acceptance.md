# Standalone Job Search human acceptance

Open Frappe Desk (`/app`) and the **Job Search** Workspace.

1. Open **Job Search Opportunity**. Confirm you can read job title, employer,
   original posting, latest revision, agent's cited research and recommendation.
2. Inspect **Job Search Employer**, **Job Search Task**, Posting, Research,
   Application, Interview and Decision lists.
3. When an agent creates a pending review, open the assigned Job Search
   Opportunity. Click **Record Decision** and confirm a native modal appears,
   offering only decisions appropriate to the pending request, plus a required
   rationale.
4. Submit **Decline** on synthetic test data. Verify the stage immediately
   becomes Closed, review Completed, the linked Job Search Task Done, and the
   immutable decision history records the signed-in human and rationale.
5. Verify no permanent blank decision/rationale inputs remain visible on the form.
6. Verify a user with **Job Search Operator** but not Approver cannot record a
   human decision; verify the human reviewer can access the assigned record.
7. Check task reminders, external application confirmations, interview notes,
   and historical posting revisions. Approval is never external submission.
8. After upgrading a prior CRM-backed site, check all historical opportunities,
   employers, tasks, comments/assignments and research records retain their links.

Browser UX acceptance is separate from backend API and schema smoke tests.
