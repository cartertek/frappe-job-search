// Configure selectable heuristics without modifying saved claims on form load.
async function sync_research_heuristics(frm) {
  const search_name = frm.doc.active_job_search;
  if (!search_name) return;
  const serial = (frm._claims_request || 0) + 1;
  frm._claims_request = serial;
  const search = await frappe.db.get_doc('Job Search Search', search_name);
  if (frm.doc.active_job_search !== search_name || frm._claims_request !== serial) return;
  const titles = (search.title_matches || '').split('\n').map(x => x.trim()).filter(Boolean);
  const defined = [
    ...(titles.length ? [{name:'builtin:job-title', heuristic_name:'Job Title',
      description:'The title or job description should match one of: ' + titles.join(', ')}] : []),
    ...(search.heuristics || []),
  ];
  if (search.salary_min && search.allow_compensation_heuristic) {
    defined.push({name:'builtin:minimum-compensation', heuristic_name:'Minimum Compensation',
      description:'Expected well above minimum: ' + [search.salary_min,search.currency,search.compensation_period].filter(Boolean).join(' ')});
  }
  frm._claim_definitions = defined;
  const grid = frm.fields_dict.research_heuristics?.grid;
  if (grid) {
    grid.update_docfield_property('heuristic_name','options',['',...defined.map(row=>row.heuristic_name)].join('\n'));
    frm.refresh_field('research_heuristics');
  }
}

frappe.ui.form.on('Job Search Heuristic Value', {
  heuristic_name(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    const definition = (frm._claim_definitions || []).find(x=>x.heuristic_name===row.heuristic_name);
    if (definition) {
      frappe.model.set_value(cdt,cdn,'heuristic_id',definition.name);
    }
  },
});

frappe.ui.form.on('Job Search Opportunity', {
  active_job_search(frm) { sync_research_heuristics(frm); },
  compensation_not_given(frm) {
    if (frm.doc.compensation_not_given) {
      ['compensation_min', 'compensation_max', 'currency', 'compensation_period'].forEach(
        field => frm.set_value(field, null));
    }
  },
  onload(frm) { if (frm.doc.active_job_search) sync_research_heuristics(frm); },
  refresh(frm) {
    if (frm.doc.active_job_search) {
      frm.add_custom_button(__('Load Heuristic Choices'), () =>
        sync_research_heuristics(frm), __('More Actions'));
    }
    const status = frm.doc.status;
    const colors = {
      Discovered: 'gray', Researching: 'yellow', 'Ready to Review': 'blue',
      Qualified: 'green', Applied: 'gray', Interviewing: 'green',
      Accepted: 'gray', Rejected: 'red',
    };
    if (status) frm.page.set_indicator(__(status), colors[status] || 'blue');
    if (frm.is_new()) return;

    const execute = async (action, values = {}) => {
      const scopes = {'Search Only':'search','Job Globally':'job',
        'Entire Organization':'organization'};
      if (values.scope) values.scope = scopes[values.scope] || values.scope;
      if (action === 'ready_to_review') {
        await sync_research_heuristics(frm);
        if (frm.is_dirty()) await frm.save();
      }
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
          } catch (error) {
            frappe.msgprint({title: __('Reject action failed'),
              message: __('The Job was not rejected. Review the error and try again.'),
              indicator: 'red'});
            throw error;
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
          options:'Search Only\nJob Globally\nEntire Organization', default:'Search Only',
          description:__('Search only, all searches for this job, or all jobs at the organization')},
        {fieldname:'search',label:__('Search'),fieldtype:'Link',options:'Job Search Search',
          default:frm.doc.active_job_search || '',
          depends_on:'eval:doc.scope=="Search Only"',mandatory_depends_on:'eval:doc.scope=="Search Only"'},
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
    if (status !== 'Ready to Review' && status !== 'Rejected') {
      frm.add_custom_button(__('Reject'), reject, __('More Actions'));
    }
  },
});
