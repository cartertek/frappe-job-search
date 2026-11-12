# Job Search collections and research strategies

**Organization** (`Job Search Employer`) is an independent employer record. **Job** is an independent, specific position. **Opportunity** is the hiring pursuit at an Organization and references one or more Jobs; presume one Opportunity per Organization unless distinct hiring teams/divisions justify separation. **Job Search Search** evaluates reusable criteria against linked Jobs and returns matching Opportunities. A single Opportunity can participate in multiple Searches, and Searches never own or duplicate Jobs or Opportunities.

## Deterministic filters and eligibility

Each Search can filter Job attributes: location, employment type, work arrangement, seniority, evidenced Last Active Date within a rolling Active In the Past interval, and minimum compensation with currency and period. Unset filters impose no restriction. Job titles to match are a **heuristic**, not an exact string filter. When salary is unpublished, Compensation Not Given bypasses numeric pay comparison, and an optional configured built-in Minimum Compensation heuristic can assess expected pay for Ready to Review.

The Search returns one **Opportunity** per matching hiring effort, with all the matching Job IDs. A Job with Closed or Rejected availability is excluded. Organization-wide rejection and Opportunity-global rejection take precedence over explicit Include, followed by the Search's per-Opportunity Exclude. An Include override can admit a Job-supported Opportunity despite filters for discovery, but **never bypasses Ready to Review evidence requirements**. When Require Explicit Heuristic Approval is enabled, an Include override is required for inclusion.

## Heuristics, claims, and research strategies

Search criteria include individually named heuristic instructions and optionally a built-in Job Title heuristic generated from reference titles. **Job** owns the specific claim records and evidence: heuristic ID/name, exact quotation, nonblank reasoning, source URL, and published Source Date (`YYYY-MM-DD` or `None`). The selected Search controls the required heuristic set and active-date cutoff. The researcher must verify that shared evidence actually applies to the Job being qualified. Claims do not automatically approve an Opportunity.

Reusable top-level **Research Strategy** records describe *how* to research. Assign strategies through the Search's **Assigned Research Strategies** child table; each assignment can optionally override its default numeric priority. Lower positive priorities execute first; blank or zero inherits the default. Follow **every** assigned strategy in effective-priority order, using `job_search.api.get_search_research_strategies(search)` as the authoritative instructions. Strategies are separate from heuristic evaluations.

## Rejections and overrides

The Search's **Explicit Opportunity Overrides** table maps one Opportunity to Include/Exclude, with Default removing its row. Search-only exclusion applies to that Search only; it does not change the Opportunity's shared pursuit stage. Use the Opportunity's Reject action for Opportunity-global or Organization-wide rejection. Independently rejecting a Job changes only Job availability and prevents that Job from qualifying, without rejecting its associated Opportunities.

Open the **Job Search** workspace and select a Search. **View Matching Opportunities** returns each qualified-by-filters Opportunity with its matching Job IDs. **Remove** creates a Search-only Opportunity exclusion. Manage all associated Jobs from their Opportunity's **Jobs** child table, and use the independent Jobs list to research opening-specific evidence.

See [Opportunity workflows](workflows.md), [Architecture](architecture.md), and [API](api.md).
