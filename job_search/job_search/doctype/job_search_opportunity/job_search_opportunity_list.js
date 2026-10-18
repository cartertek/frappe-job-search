frappe.listview_settings['Job Search Opportunity'] = {
  add_fields: ['globally_rejected'],
  get_indicator(doc) {
    if (doc.globally_rejected) return [__('Rejected'), 'red', 'globally_rejected,=,1'];
  },
};
