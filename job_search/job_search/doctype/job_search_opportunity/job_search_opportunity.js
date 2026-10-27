frappe.ui.form.on('Job Search Opportunity', {
  refresh(frm) {
    if (frm.doc.status) {
      const indicators = {
        Discovered: 'blue', Researching: 'orange', Qualified: 'green',
        Preparing: 'blue', Applied: 'blue', Screening: 'orange',
        Interviewing: 'orange', Offer: 'purple', Accepted: 'green',
        Rejected: 'red', Withdrawn: 'gray', Closed: 'gray',
      };
      frm.page.set_indicator(__(frm.doc.status), indicators[frm.doc.status] || 'blue');
    }
    if (frm.is_new()) return;
    if (!frm.doc.globally_rejected) {
      frm.add_custom_button(__('Reject Job Globally'), async () => {
        frappe.confirm(__('Hide this job from every search?'), async () => {
          await frappe.call({method: 'job_search.api.reject_job', args: {job: frm.doc.name}});
          await frm.reload_doc();
        });
      });
    }
    if (frm.doc.review_status === 'Pending') {
      const choices = {
        'Pursue or Decline': ['Pursue', 'Decline'],
        'Authorize or Decline Application': ['Authorize Application', 'Decline Application'],
        'Accept or Reject Offer': ['Accept Offer', 'Reject Offer'],
        'Withdraw': ['Withdraw'],
        'Override': ['Override'],
      }[frm.doc.review_request] || [];
      if (choices.length) {
        frm.add_custom_button(__('Record Decision'), () => {
          const dialog = new frappe.ui.Dialog({
            title: __('Record Human Decision'),
            fields: [
              {fieldname: 'decision', label: __('Decision'), fieldtype: 'Select',
                options: choices.join('\n'), reqd: 1},
              {fieldname: 'rationale', label: __('Rationale'), fieldtype: 'Small Text', reqd: 1},
            ],
            primary_action_label: __('Submit Decision'),
            primary_action: async (values) => {
              if (!values?.decision || !values?.rationale?.trim()) return;
              dialog.get_primary_btn().prop('disabled', true);
              try {
                await frappe.call({method: 'job_search.api.record_human_decision',
                  args: {opportunity: frm.doc.name, decision: values.decision,
                    rationale: values.rationale.trim()}});
                dialog.hide();
                await frm.reload_doc();
                frappe.show_alert({message: __('Decision recorded'), indicator: 'green'});
              } finally {
                dialog.get_primary_btn().prop('disabled', false);
              }
            },
          });
          dialog.show();
        });
      }
    }
  },
});
