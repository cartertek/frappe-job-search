// Job Title is editable under Job Search Fields, but is also summarized in Overview.
// Escape user-entered content before displaying it in an HTML field.
function render_overview_title(frm) {
  const title = frm.doc.job_title ? frappe.utils.escape_html(frm.doc.job_title) :
    `<span class="text-muted">${__('Not set')}</span>`;
  frm.fields_dict.overview_job_title?.html(`
    <div class="job-search-overview-title">
      <div class="control-label">${__('Job Title')}</div>
      <div class="job-search-overview-title-value">${title}</div>
    </div>
  `);
}

// Keep the job's assessment rows aligned to the search's stable child-row IDs.
// Preserve answers while changing descriptions; never silently discard answers.
async function sync_research_heuristics(frm, confirm_discard = false) {
  const name = frm.doc.active_job_search;
  if (!name) return;
  const request = (frm._heuristic_sync_request || 0) + 1;
  frm._heuristic_sync_request = request;
  const search = await frappe.db.get_doc('Job Search Search', name);
  if (frm.doc.active_job_search !== name || frm._heuristic_sync_request !== request) return;

  const titles = (search.title_matches || '').split('\n').map(s => s.trim()).filter(Boolean);
  const defined = [
    ...(titles.length ? [{name: 'builtin:job-title', heuristic_name: 'Job Title',
      description: 'The job title should be similar to one of the titles below and/or the job description should describe a role matching one of these titles. Assess the meaning of the role, not an exact text match.\n\nTitles:\n' + titles.map(t => '- ' + t).join('\n')}] : []),
    ...(search.heuristics || []),
  ];
  const current = frm.doc.research_heuristics || [];
  const expected_ids = new Set(defined.map(row => row.name));
  const stale = current.filter(row => !expected_ids.has(row.heuristic_id));
  const has_stale_answers = stale.some(row => (row.value || '').trim());
  if (has_stale_answers) {
    if (!confirm_discard) {
      frm.dashboard.set_headline_alert(
        __('This search has different research heuristics. Sync the table to replace outdated answers.'),
        'orange'
      );
      return;
    }
    const agreed = await new Promise(resolve => frappe.confirm(
      __('Changing this search will discard answers for heuristics that do not belong to it. Continue?'),
      () => resolve(true), () => resolve(false)
    ));
    if (!agreed || frm.doc.active_job_search !== name) return;
  }

  const by_id = new Map(current.map(row => [row.heuristic_id, row]));
  const unchanged = current.length === defined.length && defined.every((row, i) =>
    current[i].heuristic_id === row.name && current[i].heuristic_name === row.heuristic_name &&
    current[i].description === row.description
  );
  if (unchanged) return;

  frm.clear_table('research_heuristics');
  defined.forEach(heuristic => {
    const row = frm.add_child('research_heuristics');
    row.heuristic_id = heuristic.name;
    row.heuristic_name = heuristic.heuristic_name;
    row.description = heuristic.description;
    row.value = by_id.get(heuristic.name)?.value || '';
  });
  frm.refresh_field('research_heuristics');
  frm.dirty();
}

frappe.ui.form.on('Job Search Opportunity', {
  job_title(frm) { render_overview_title(frm); },
  active_job_search(frm) { sync_research_heuristics(frm, true); },
  refresh(frm) {
    render_overview_title(frm);
    sync_research_heuristics(frm);
    if (frm.doc.active_job_search) {
      frm.add_custom_button(__('Sync Research Heuristics'), () =>
        sync_research_heuristics(frm, true), __('More Actions'));
    }
    const status = frm.doc.status;
    const colors = {
      Discovered: 'blue', Researching: 'orange', 'Ready to Review': 'orange',
      Qualified: 'green', Applied: 'blue', Interviewing: 'orange',
      Accepted: 'green', Rejected: 'red',
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
