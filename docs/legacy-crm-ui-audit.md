# CRM integration audit

**Updated:** See [human acceptance checklist](human-acceptance.md) for current status and remaining browser tests.

The first audit considered missing UI for all agent-only actions a defect. The implementation instead keeps research, sources, procedures and related records API-driven for agents, and exposes human-facing summaries, approvals, feedback and work queues in Frappe CRM. The outstanding criteria are human browser acceptance, regression tests, deployment hardening and any UX refinements revealed by actual use.

## Current architecture (post-issue #15)

This is a **historical CRM-era UI audit**, not current operating guidance. The active app is standalone Frappe v16, with separate **Job**, **Opportunity**, and **Organization** records and a Desk Workspace, not Frappe CRM forms. Review, follow-up, interview, Activity Log and approval workflows operate on Opportunities. Refer to [Architecture](architecture.md), [Workflows](workflows.md), and [Human acceptance](human-acceptance.md) for current instructions.
