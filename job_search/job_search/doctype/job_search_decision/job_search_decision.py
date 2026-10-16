import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

from job_search.permissions import require_approver, require_opportunity


class JobSearchDecision(Document):
    def before_insert(self):
        require_approver()
        require_opportunity(self.opportunity, "read")
        if not (self.rationale or "").strip():
            frappe.throw("Authorization rationale required")
        self.authorized_by = frappe.session.user
        self.authorized_at = now_datetime()
        self.used_for = None

    def validate(self):
        require_approver()
        if not self.is_new():
            frappe.throw("Decisions are immutable. Create a new decision to supersede one.")

    def on_trash(self):
        frappe.throw("Authorization records cannot be deleted")
