frappe.ui.form.on('Job Search Search', {
  refresh(frm) {
    if (frm.is_new()) return;
    frm.add_custom_button(__('View Matching Opportunities'), async () => {
      const {message} = await frappe.call({
        method: 'job_search.api.get_search_results', args: {search:frm.doc.name},
      });
      const opportunities = message.data.opportunities || [];
      const esc = value => frappe.utils.escape_html(String(value || ''));
      const rows = opportunities.map(opp => `
        <tr>
          <td><a href="${esc(frappe.utils.get_form_link('Opportunity', opp.opportunity))}">${esc(opp.opportunity_name)}</a></td>
          <td>${esc(opp.organization_name || opp.organization)}</td>
          <td>${esc((opp.qualifying_job_labels || opp.qualifying_jobs || []).join(', '))}</td>
          <td>${esc(opp.match_reason)}</td>
          <td><button type="button" class="btn btn-xs btn-default" data-remove="${esc(opp.opportunity)}">Remove</button></td>
        </tr>`).join('');
      const html = `<div class="js-results" style="max-height:60vh;overflow:auto">
        <p>${opportunities.length} matching opportunities. Remove excludes an opportunity from this Search only.</p>
        <table class="table table-bordered"><thead><tr>
          <th>Opportunity</th><th>Organization</th><th>Matching Jobs</th><th>Match</th><th></th>
        </tr></thead><tbody>${rows || '<tr><td colspan="5">No opportunities match this search.</td></tr>'}</tbody></table>
      </div>`;
      const dialog = new frappe.ui.Dialog({title:__('Matching Opportunities'),size:'extra-large',
        fields:[{fieldname:'results',fieldtype:'HTML'}]});
      dialog.show();
      dialog.fields_dict.results.$wrapper.html(html);
      dialog.fields_dict.results.$wrapper.on('click','[data-remove]',async event => {
        const button=event.currentTarget;
        button.disabled=true;
        try {
          await frappe.call({method:'job_search.api.set_search_membership',
            args:{search:frm.doc.name,opportunity:button.dataset.remove,override:'Exclude'}});
          $(button).closest('tr').remove();
          await frm.reload_doc();
        } catch(error) {button.disabled=false;throw error;}
      });
    });
  },
});
