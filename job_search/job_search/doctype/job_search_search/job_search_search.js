// Frappe's default child grid strips rich text and truncates static cells.
// Render a sanitized, full-height rich-text preview inside each heuristic row.
function show_heuristic_description(gridRow) {
  if (gridRow.grid?.df?.fieldname !== 'heuristics' || !gridRow.doc) return;
  const column = gridRow.columns?.description;
  if (!column?.static_area) return;
  const html = gridRow.doc.description || '';
  const safe = frappe.utils.sanitize_html ? frappe.utils.sanitize_html(html)
    : frappe.utils.escape_html(html);
  column.static_area.html(`<div class="job-search-heuristic-richtext">${safe}</div>`);
  $(gridRow.row).addClass('job-search-heuristic-row');
}

frappe.ui.form.on('Job Search Search', {
  onload(frm) {
    if (!document.getElementById('job-search-heuristic-grid-css')) {
      $('<style id="job-search-heuristic-grid-css">' +
        '.job-search-heuristic-row, .job-search-heuristic-row .grid-static-col {' +
        'height:auto!important;min-height:38px;align-items:flex-start!important}' +
        '.job-search-heuristic-row .static-area {' +
        'height:auto!important;max-height:none!important;overflow:visible!important;' +
        'white-space:normal!important;text-overflow:clip!important}' +
        '.job-search-heuristic-richtext {white-space:normal;overflow-wrap:anywhere;' +
        'line-height:1.5;padding:4px 0}' +
        '.job-search-heuristic-richtext p {margin:0 0 6px}' +
        '.job-search-heuristic-richtext ul,.job-search-heuristic-richtext ol {' +
        'padding-left:24px;margin:0 0 6px}' +
        '</style>').appendTo('head');
    }
    $(frm.wrapper).off('grid-row-render.job-search-heuristics')
      .on('grid-row-render.job-search-heuristics', (_event, row) => {
        show_heuristic_description(row);
      });
  },
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
          <td><a href="/desk/job-search-opportunity/${encodeURIComponent(job.name)}">${esc(job.job_title)}</a></td>
          <td>${esc(job.organization)}</td>
          <td>${esc(job.location)}</td>
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
