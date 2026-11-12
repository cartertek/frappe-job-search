frappe.ui.form.on('Job Search Employer', {
  refresh(frm) {
    if (frm.is_new() || !frm.doc.globally_rejected) return;
    frm.add_custom_button(__('Reopen Organization'), () => {
      const dialog=new frappe.ui.Dialog({title:__('Reopen Organization'),
        fields:[{fieldname:'reason',label:__('Reason'),fieldtype:'Small Text',reqd:1}],
        primary_action_label:__('Reopen'),
        primary_action: async values => {
          await frappe.call({method:'job_search.api.reopen_organization',
            args:{organization:frm.doc.name,reason:values.reason}});
          dialog.hide();await frm.reload_doc();
        }});
      dialog.show();
    });
  },
});
