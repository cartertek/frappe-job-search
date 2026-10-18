frappe.ui.form.on('Job Search Employer', {
  refresh(frm) {
    if (frm.is_new() || frm.doc.globally_rejected) return;
    frm.add_custom_button(__('Reject Organization Globally'), () => {
      frappe.confirm(__('Hide all jobs from this organization in every search?'), async () => {
        await frappe.call({method: 'job_search.api.reject_organization',
          args: {organization: frm.doc.name}});
        await frm.reload_doc();
      });
    });
  },
});
