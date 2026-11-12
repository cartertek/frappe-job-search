frappe.ui.form.on('Opportunity', {
  refresh(frm) {
    const status = frm.doc.status;
    const colors = {Discovered:'gray', Researching:'yellow', 'Ready to Review':'blue',
      Qualified:'green', Applied:'gray', Interviewing:'green', Accepted:'gray', Rejected:'red'};
    if (status) frm.page.set_indicator(__(status), colors[status] || 'blue');
    if (frm.is_new()) return;
    const run = async (action, values={}) => {
      try {
        await frappe.call({method:'job_search.api.perform_opportunity_action',
          args:{opportunity:frm.doc.name, action, ...values}});
        await frm.reload_doc();
      } catch (error) {
        frappe.msgprint({title:__('Opportunity action failed'),
          message:__('Review the error and try again.'),indicator:'red'});
        throw error;
      }
    };
    const dialog = (label, fields, action) => {
      const modal = new frappe.ui.Dialog({title:__(label),fields,primary_action_label:__(label),
        primary_action: async values => {
          modal.get_primary_btn().prop('disabled',true);
          try {await run(action,values);modal.hide();}
          finally {modal.get_primary_btn().prop('disabled',false);}
        }});
      modal.show();
    };
    const reason = [{fieldname:'rationale',label:__('Rationale'),fieldtype:'Small Text',reqd:1}];
    const primary = (label,action,fields=[]) => frm.page.set_primary_action(__(label),
      () => fields.length ? dialog(label,fields,action) : run(action));
    const reject = () => dialog('Reject Opportunity',[
      {fieldname:'scope',label:__('Reject From'),fieldtype:'Select',reqd:1,
       options:'Search Only\nOpportunity Globally\nEntire Organization',default:'Search Only'},
      {fieldname:'search',label:__('Search'),fieldtype:'Link',options:'Job Search Search',
       default:frm.doc.active_job_search||'',depends_on:'eval:doc.scope=="Search Only"',
       mandatory_depends_on:'eval:doc.scope=="Search Only"'},
      ...reason], 'reject');
    if (status === 'Rejected') primary('Reopen Opportunity','reopen',reason);
    else if (frm.doc.rejection_scope === 'Search Only') frm.add_custom_button(
      __('Clear Search Rejection'),()=>dialog('Clear Search Rejection',reason,'reopen'),__('More Actions'));
    if (status === 'Discovered') primary('Begin Research','begin_research');
    if (status === 'Researching') primary('Ready to Review','ready_to_review');
    if (status === 'Ready to Review') {
      primary('Mark Qualified','qualify',reason);
      frm.add_custom_button(__('Needs Research'),()=>run('needs_research'));
    }
    if (status === 'Qualified') primary('Mark Applied','mark_applied');
    if (status === 'Applied') primary('Begin Interviewing','begin_interviewing');
    if (status === 'Interviewing') primary('Accept Offer','accept_offer',[
      {fieldname:'offer_details',label:__('Offer Details'),fieldtype:'Small Text',reqd:1,
       default:frm.doc.offer_details||''},...reason]);
    if (status !== 'Rejected') frm.add_custom_button(__('Reject Opportunity'),reject,
      __('More Actions'));
  },
});
