frappe.ui.form.on('Job Search Search', {
  refresh(frm) {
    if (frm.is_new()) return;
    frm.add_custom_button(__('View Matching Jobs'), async () => {
      const { message } = await frappe.call({
        method: 'job_search.api.get_search_results',
        args: { search: frm.doc.name },
      });
      const jobs = message.data.jobs;
      const esc = (value) => frappe.utils.escape_html(String(value || ''));
      const rows = jobs.map(job => `
        <tr>
          <td><a href="/desk/job-search-opportunity/${encodeURIComponent(job.name)}">${esc(job.js_job_title)}</a></td>
          <td>${esc(job.organization)}</td>
          <td>${esc(job.js_location)}</td>
          <td>${esc(job.match_reason)}</td>
          <td><button type="button" class="btn btn-xs btn-default" data-remove="${esc(job.name)}">Remove</button></td>
        </tr>`).join('');
      const html = `<div class="js-results" style="max-height:60vh;overflow:auto">
        <p>${jobs.length} matching jobs. Remove excludes a job from this search only.</p>
        <table class="table table-bordered"><thead><tr>
          <th>Job</th><th>Organization</th><th>Location</th><th>Match</th><th></th>
        </tr></thead><tbody>${rows || '<tr><td colspan="5">No jobs match this search.</td></tr>'}</tbody></table>
      </div>`;
      const dialog = new frappe.ui.Dialog({
        title: __('Matching Jobs'), size: 'extra-large',
        fields: [{fieldname:'results',fieldtype:'HTML'}],
      });
      dialog.show();
      dialog.fields_dict.results.$wrapper.html(html);
      dialog.fields_dict.results.$wrapper.on('click', '[data-remove]', async (event) => {
        const button = event.currentTarget;
        button.disabled = true;
        try {
          await frappe.call({method: 'job_search.api.set_search_membership',
            args: {search: frm.doc.name, job: button.dataset.remove, override: 'Exclude'}});
          $(button).closest('tr').remove();
          await frm.reload_doc();
        } catch (error) { button.disabled = false; throw error; }
      });
    });
  },
});
