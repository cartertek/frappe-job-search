# Job workflow

The Job has eight statuses: **Discovered → Researching → Ready to Review → Qualified → Applied → Interviewing → Accepted**, plus **Rejected**. It does not have Preparing, Screening, Offer, Withdrawn or Closed statuses.

| Current status | Human action | Result |
|---|---|---|
| Discovered | Agent begins research | Researching |
| Researching | Ready to Review | Ready to Review, only after a selected active search matches and every research heuristic has a nonempty value |
| Ready to Review | **Mark Qualified** (primary) | Qualified; requires research, completed procedure and a reasoned human approval |
| Ready to Review | **Needs Research** | Researching |
| Ready to Review | **Reject** | Scoped exclusion or global rejection; see below |
| Qualified | **Mark Applied** (primary) | Applied, only after a confirmed, authorized application is recorded |
| Applied | **Begin Interviewing** (primary) | Interviewing, requires an interview record |
| Interviewing | **Accept Offer** (primary) | Accepted, requires offer details and a reasoned human approval |

Reject is also in **More Actions** on Discovered, Researching, Qualified, Applied and Interviewing. The rejection modal takes a rationale and scope: **this search** (explicit Exclude), **this job globally** (global rejection and Rejected status), or **this organization globally** (all its jobs excluded). Search-specific exclusion leaves the job's global workflow status unchanged; global organization rejection hides every job from the organization's searches. Global rejection overrides explicit search inclusion.

The agent APIs and form edits are subject to the same server-side transition validations. Historical transition records are retained. Existing old statuses migrate as follows: Preparing → Qualified, Screening → Applied, Offer → Interviewing, Withdrawn and Closed → Rejected. No history is discarded. Reopening a Rejected job to Researching still requires an approved exception.

## Ready to Review readiness gate

A Job's **Active Job Search** link in **Job Search Fields** names the search used to evaluate readiness. The **Research Heuristics** child table, immediately after Job Details, contains the corresponding heuristic names, descriptions and researcher-entered **Value** for each criterion. Selecting a search or using **More Actions → Sync Research Heuristics** fills the table from the search; values already attached to unchanged heuristic IDs are preserved, and dropping answers for removed criteria requires confirmation. Save the answers before review.

Both **Ready to Review** on the form and `transition_opportunity(..., stage="Ready to Review")` enforce the gate in the server's Job validation hook. A ready job must name an **enabled** search; match **every deterministic filter** (including complete title, location, compensation and posting date); be neither globally rejected nor excluded by that search; have an explicit **Include** when the search requires heuristic approval; and have **one nonempty Value per current search heuristic**. Missing, duplicate or unrelated heuristic rows are reported. The rejection message lists *all* failing checks.

An Include override may make a job appear in **search results** even when filters do not match, but **does not bypass the stricter Ready to Review gate**. An approved workflow exception does not bypass this gate either. Draft jobs remain editable while research is incomplete; no existing jobs are silently moved to another stage.
