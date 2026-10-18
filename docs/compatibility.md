# Compatibility

- **Frappe:** stable version-16 (tested live with 16.52.0), Python 3.14, MariaDB.
- **Frappe CRM:** not required for new installations or runtime after migration.
  It is required *temporarily* on an existing CRM-backed site during historical
  data import and may be uninstalled only afterward.
- **Frappe Wiki:** optional and selected independently by the platform image.

App-owned DocTypes and API methods have been tested on the existing deployed
Frappe 16 site following migration. A clean-site CI installation on the final
CRM-free image is the deployment release gate.
