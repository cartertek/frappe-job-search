frappe.ui.form.on('Opportunity', {
  activity_log_add(frm, cdt, cdn) {
    // Frappe's Add Row handler focuses the first editable field (Date) after
    // 100ms. Focus the required Type selector for this child table instead.
    setTimeout(() => {
      const row = frm.fields_dict.activity_log?.grid?.grid_rows_by_docname?.[cdn];
      row?.row?.find('[data-fieldname="type"] select:visible').first().trigger('focus');
    }, 180);
  },
  onload(frm) {
    // Existing Activity rows must display oldest first, even before save.
    const rows = frm.doc.activity_log || [];
    if (rows.length < 2) return;
    rows.sort((a,b) => String(a.date || '').localeCompare(String(b.date || '')));
    rows.forEach((row,i) => { row.idx = i+1; });
    frm.refresh_field('activity_log');
  },
  refresh(frm) {
    const status = frm.doc.status;
    const colors = {Discovered:'gray', Researching:'yellow', 'Ready to Review':'blue',
      Qualified:'green', Applied:'gray', Interviewing:'green', Accepted:'gray', Rejected:'red'};
    if (status) frm.page.set_indicator(__(status), colors[status] || 'blue');
    if (frm.is_new()) return;
    const run = async (action, values={}) => {
      try {
        // Save any edited Activity Log rows before attempting a stage change.
        if (frm.is_dirty()) await frm.save();
        await frappe.call({method:'job_search.api.perform_opportunity_action',
          args:{opportunity:frm.doc.name, action, ...values}});
        await frm.reload_doc();
      } catch (error) {
        frappe.msgprint({title:__('Opportunity action failed'),
          message:__('Could not update {0}. See the error details above.',
          [frappe.utils.escape_html(frm.doc.opportunity_name || frm.doc.name)]),indicator:'red'});
        throw error;
      }
    };
    const dialog = (label, fields, action) => {
      const modal = new frappe.ui.Dialog({title:__(label),fields,primary_action_label:__(label),
        primary_action: async values => {
          modal.get_primary_btn().prop('disabled',true);
          try {
            const scopeValues = {'Search Only':'search',
              'Opportunity Globally':'opportunity', 'Entire Organization':'organization'};
            const args = action === 'reject'
              ? {...values, scope:scopeValues[values.scope] || values.scope} : values;
            await run(action,args);
            modal.hide();
          }
          finally {modal.get_primary_btn().prop('disabled',false);}
        }});
      modal.show();
    };
    const activityTypes = {mark_applied:'Application',
      begin_interviewing:'Interview', accept_offer:'Acceptation'};
    const activityFields = [
      {fieldname:'activity_date',label:__('Date'),fieldtype:'Date',
        default:frappe.datetime.get_today(),reqd:1},
      {fieldname:'activity_contact',label:__('Contact'),fieldtype:'Data'},
      {fieldname:'activity_platform',label:__('Platform'),fieldtype:'Data'},
      {fieldname:'activity_notes',label:__('Notes'),fieldtype:'Small Text'},
    ];
    const activityAction = (label,action,otherFields=[]) => {
      const type=activityTypes[action];
      const exists=(frm.doc.activity_log || []).some(row=>row.type===type);
      if (exists && !otherFields.length) return run(action);
      const fields=exists ? otherFields : [...activityFields,...otherFields];
      const modal=new frappe.ui.Dialog({title:__(label),fields,
        primary_action_label:__(label),primary_action:async values=>{
          const args={...values};
          if (!exists) {
            args.activity={date:values.activity_date,contact:values.activity_contact,
              platform:values.activity_platform,notes:values.activity_notes};
            delete args.activity_date;
            delete args.activity_contact;
            delete args.activity_platform;
            delete args.activity_notes;
          }
          modal.get_primary_btn().prop('disabled',true);
          try {await run(action,args);modal.hide();}
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
      primary('Mark Qualified','qualify');
      frm.add_custom_button(__('Needs Research'),()=>run('needs_research'));
    }
    if (status === 'Qualified') frm.page.set_primary_action(__('Mark Applied'),
      () => activityAction('Mark Applied','mark_applied'));
    if (status === 'Applied') frm.page.set_primary_action(__('Begin Interviewing'),
      () => activityAction('Begin Interviewing','begin_interviewing'));
    if (status === 'Interviewing') frm.page.set_primary_action(__('Accept Offer'),
      () => activityAction('Accept Offer','accept_offer',[
      {fieldname:'offer_details',label:__('Offer Details'),fieldtype:'Small Text',reqd:1,
       default:frm.doc.offer_details||''},...reason]));
    if (status !== 'Rejected') frm.add_custom_button(__('Reject Opportunity'),reject,
      __('More Actions'));
  },
});
