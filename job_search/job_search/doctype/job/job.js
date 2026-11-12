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

frappe.ui.form.on('Job', {
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
    const colors = {Unknown:'gray', Active:'green', Closed:'orange', Rejected:'red'};
    if (frm.doc.availability_status) frm.page.set_indicator(
      __(frm.doc.availability_status), colors[frm.doc.availability_status] || 'gray');
    if (frm.is_new()) return;
    const act = (action) => {
      const dialog = new frappe.ui.Dialog({
        title: __(action === 'reject_job' ? 'Reject Job' : 'Reopen Job'),
        fields:[{fieldname:'reason',label:__('Reason'),fieldtype:'Small Text',reqd:1}],
        primary_action_label: __('Confirm'),
        primary_action: async values => {
          try {
            await frappe.call({method:'job_search.api.'+action,
              args:{job:frm.doc.name,reason:values.reason}});
            dialog.hide();
            await frm.reload_doc();
          } catch (error) { frappe.msgprint({message:__('Job action failed'),indicator:'red'}); throw error; }
        },
      });
      dialog.show();
    };
    if (frm.doc.availability_status === 'Rejected') {
      frm.add_custom_button(__('Reopen Job'), () => act('reopen_job'));
    } else {
      frm.add_custom_button(__('Reject Job'), () => act('reject_job'), __('More Actions'));
    }
  },
});
