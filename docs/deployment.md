# Deployment and maintenance

Use a separate Frappe `version-16` bench (v16.50+ navigation, Python 3.14) with stable CRM `main` installed. See [compatibility](compatibility.md). Back up target site before deploying. Install app and migrate, then inspect fixture-imported Custom Fields on CRM Deal, Organization and Task, the JS: status records, and the initial procedure versions.

Give a dedicated operator Job Search Operator plus CRM Sales role as required for native CRM permissions. Assign Job Search Approver only to a human decision-maker. Verify API authentication attribution.

In Desk, verify Job Search appears in the **Apps** screen and its shipped **Dock** and **Job Search module Sidebar** appear. Check the Job Search Workspace and linked DocTypes. In CRM, verify that the seeded Job Search Pipeline and Research Queue views are accessible and filter Deals correctly. Test custom field rendering, Deal creation, native Kanban status changes and the documented REST methods. Test posting import twice, then altered posting content at the same URL; verify the earlier snapshot remains immutable. Test one linked Task per stage transition, overdue task queues and missing-research queue. Test denied transitions for missing evidence and approvals; check that ordinary CRM Deals remain unchanged.

Before production use, run an end-to-end integration suite, verify site migrations, perform backup and restore into a separate test site, and test compatibility with the intended pinned CRM release. For backup, use bench --site SITE backup --with-files. Restore using documented bench restore commands on a separate site; inspect attachments, source links and approvals.

Never erase a posted description, procedure execution, approval or application to correct data. Add an explanatory revision or linked record.
