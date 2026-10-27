frappe.ui.form.on('Job Search Opportunity', {
  refresh(frm) {
    const status = frm.doc.status;
    const colors = {
      Discovered: 'blue', Researching: 'orange', 'Ready to Review': 'orange',
      Qualified: 'green', Applied: 'blue', Interviewing: 'orange',
      Accepted: 'green', Rejected: 'red',
    };
    if (status) frm.page.set_indicator(__(status), colors[status] || 'blue');
    if (frm.is_new()) return;

    const execute = async (action, values = {}) => {
      await frappe.call({
        method: 'job_search.api.perform_job_action',
        args: {opportunity: frm.doc.name, action, ...values},
      });
      await frm.reload_doc();
    };
    const dialog = (title, fields, action, label = title) => {
      const modal = new frappe.ui.Dialog({
        title: __(title), fields, primary_action_label: __(label),
        primary_action: async values => {
          modal.get_primary_btn().prop('disabled', true);
          try {
            await execute(action, values);
            modal.hide();
          } finally { modal.get_primary_btn().prop('disabled', false); }
        },
      });
      modal.show();
    };
    const rationale = [{fieldname:'rationale',label:__('Rationale'),fieldtype:'Small Text',reqd:1}];
    const primary = (label, action, fields = []) => {
      frm.page.set_primary_action(__(label), () => {
        if (fields.length) dialog(label, fields, action);
        else execute(action);
      });
    };
    const reject = () => {
      dialog('Reject', [
        {fieldname:'scope', label:__('Reject From'),fieldtype:'Select',reqd:1,
          options:'search\njob\norganization', default:'search',
          description:__('Search only, all searches for this job, or all jobs at the organization')},
        {fieldname:'search',label:__('Search'),fieldtype:'Link',options:'Job Search Search',
          depends_on:'eval:doc.scope=="search"',mandatory_depends_on:'eval:doc.scope=="search"'},
        ...rationale,
      ], 'reject');
    };
    if (status === 'Researching') primary('Ready to Review', 'ready_to_review');
    if (status === 'Ready to Review') {
      primary('Mark Qualified', 'qualify', rationale);
      frm.add_custom_button(__('Needs Research'), () => execute('needs_research'));
      frm.add_custom_button(__('Reject'), reject);
    }
    if (status === 'Qualified') primary('Mark Applied', 'mark_applied');
    if (status === 'Applied') primary('Begin Interviewing', 'begin_interviewing');
    if (status === 'Interviewing') primary('Accept Offer', 'accept_offer', [
      {fieldname:'offer_details',label:__('Offer Details'),fieldtype:'Small Text',reqd:1,
        default:frm.doc.offer_details || ''}, ...rationale,
    ]);
    if (status !== 'Ready to Review' && status !== 'Rejected' && status !== 'Accepted') {
      frm.add_custom_button(__('Reject'), reject, __('More Actions'));
    }
  },
});
