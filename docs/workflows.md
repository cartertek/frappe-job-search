# Job workflow

The Job has eight statuses: **Discovered → Researching → Ready to Review → Qualified → Applied → Interviewing → Accepted**, plus **Rejected**. It does not have Preparing, Screening, Offer, Withdrawn or Closed statuses.

| Current status | Human action | Result |
|---|---|---|
| Discovered | Agent begins research | Researching |
| Researching | Ready to Review | Ready to Review |
| Ready to Review | **Mark Qualified** (primary) | Qualified; requires research, completed procedure and a reasoned human approval |
| Ready to Review | **Needs Research** | Researching |
| Ready to Review | **Reject** | Scoped exclusion or global rejection; see below |
| Qualified | **Mark Applied** (primary) | Applied, only after a confirmed, authorized application is recorded |
| Applied | **Begin Interviewing** (primary) | Interviewing, requires an interview record |
| Interviewing | **Accept Offer** (primary) | Accepted, requires offer details and a reasoned human approval |

Reject is also in **More Actions** on Discovered, Researching, Qualified, Applied and Interviewing. The rejection modal takes a rationale and scope: **this search** (explicit Exclude), **this job globally** (global rejection and Rejected status), or **this organization globally** (all its jobs excluded). Search-specific exclusion leaves the job's global workflow status unchanged; global organization rejection hides every job from the organization's searches. Global rejection overrides explicit search inclusion.

The agent APIs and form edits are subject to the same server-side transition validations. Historical transition records are retained. Existing old statuses migrate as follows: Preparing → Qualified, Screening → Applied, Offer → Interviewing, Withdrawn and Closed → Rejected. No history is discarded. Reopening a Rejected job to Researching still requires an approved exception.
