import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class JobSearchProcedureExecution(Document):
    def validate(self):
        procedure = frappe.get_doc("Job Search Procedure", self.procedure)
        if not self.opportunity and not self.organization:
            frappe.throw("Execution requires an opportunity or organization")
        if self.opportunity:
            org = frappe.db.get_value("Job Search Opportunity", self.opportunity, "organization")
            if self.organization and org != self.organization:
                frappe.throw("Execution organization does not match the opportunity")
            self.organization = org
        previous = self.get_doc_before_save()
        if not previous:
            if procedure.status != "Active":
                frappe.throw("Only active procedures may be executed")
            self.procedure_version = procedure.version
            if not self.steps:
                self.steps = [{"step_id": s.step_id, "title": s.title, "status": "Pending"}
                              for s in procedure.steps]
            if not self.started_at:
                self.started_at = now_datetime()
            return
        if (self.procedure != previous.procedure or
                self.procedure_version != previous.procedure_version or
                self.opportunity != previous.opportunity):
            frappe.throw("Execution identity and procedure version cannot change")
        if previous.status in ("Completed", "Failed", "Cancelled"):
            frappe.throw("Terminal procedure executions are immutable")
        if self.status == "Completed":
            steps_done = {s.step_id for s in self.steps if s.status == "Completed"}
            required = {s.step_id for s in procedure.steps if s.required}
            if required - steps_done:
                frappe.throw("Required procedure steps are incomplete: " +
                             ", ".join(sorted(required - steps_done)))
            if not (self.assessment or "").strip():
                frappe.throw("Completion assessment required")
            self.completed_at = self.completed_at or now_datetime()

    def on_trash(self):
        frappe.throw("Procedure execution history must be retained")
