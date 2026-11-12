# Known limitations / release gates

- The migrated production-like site passed Frappe v16 DocType synchronization,
  historical import, reference-integrity checks and transaction-rolled-back
  workflow tests. Fresh-site image installation is verified separately in CI;
  a real signed-in human browser walkthrough is an independent release check.
- Do not uninstall CRM before historical import and verified backups; image
  rollback alone cannot undo SQL schema/DocType removal.
- Agents do not automatically submit job applications or send messages.
- Rich search/reporting and proactive notifications are not yet implemented.
- Frappe Desk is the human UI. No separate frontend application is required.
