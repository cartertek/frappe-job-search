# Frappe 16 / CRM compatibility target

**As of October 16, 2026** the implementation tracks these upstream stable branches:

| Component | Branch | Version inspected | Git commit inspected |
| --- | --- | --- | --- |
| Frappe Framework | `version-16` | 16.52.0 | `4515014` (Oct 14, 2026) |
| Frappe CRM | `main` | 1.88.0 | `0baa1e8` (Oct 15, 2026) |
| Python | Frappe 16 requirement | 3.14 | requires `>=3.14,<3.15` |

The Frappe 16.50 navigation redesign replaced app-level Workspace Sidebar files with **Apps → Dock → Sidebar**, backed by new `Dock`, `Dock Item`, `Sidebar` and `Sidebar Item` DocTypes. The app ships the current JSON fixture layouts, a standard Workspace, and `add_to_apps_screen` in hooks. Earlier Desktop Icon and Workspace Sidebar fixtures have been removed; they are not used on a fresh recent v16 site.

Frappe CRM 1.88.0 continues to expose the `CRM Deal`, `CRM Organization`, `CRM Task`, `CRM Deal Status` and `CRM View Settings` schemas used by the app. `CRM Deal.status` is a Link to CRM Deal Status and Deal has an Organization link; a CRM Task references a Deal via reference_doctype/reference_docname. CRM's `main` branch is the **stable v1** branch compatible with Frappe 16, not CRM `develop` (future v2 / Frappe 17).

Compatibility is with the **latest stable releases in these branches**, not an unsupported Frappe 17 development stack. Do not use `crm version-16` (that branch does not exist). The package requires Python 3.14 to match Frappe 16; CI static checks run on Python 3.14.

## Verification still required during installation

1. Check Frappe and CRM installed versions with `bench --site SITE list-apps` and verify `frappe` major 16 / `crm` stable v1; update together with their compatible dependencies.
2. Install Job Search onto an isolated test site and migrate; verify all 13 DocTypes and app-scoped CRM fixtures and the Dock/Sidebar exports.
3. Exercise a Deal from Discovered to Qualified, Applied, Interviewing and Closed, including unauthorized API and Desk edits.
4. Test posting snapshots, approval attribution, repeated imports, task creation, follow-up/research queues and CRM Kanban.
5. Run tests against the live database, then perform backup/restore and upgrades on the test site before production.

**Reference sources:**

- Frappe stable branch: https://github.com/frappe/frappe/tree/version-16
- CRM stable branch and compatibility: https://github.com/frappe/crm/tree/main
- Frappe 16 navigation: https://docs.frappe.io/framework/user/en/desk/navigation
- Sidebar fixture migration: https://docs.frappe.io/framework/user/en/desk/navigation/migrating-to-the-new-navigation
- Frappe apps screen: https://docs.frappe.io/framework/user/en/desk/navigation/desktop
