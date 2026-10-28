const jobStatusColors = {
  Discovered: 'gray', Researching: 'yellow', 'Ready to Review': 'blue',
  Qualified: 'green', Applied: 'gray', Interviewing: 'green',
  Accepted: 'gray', Rejected: 'red',
};

frappe.listview_settings['Job Search Opportunity'] = {
  add_fields: ['status', 'globally_rejected'],
  get_indicator(doc) {
    if (doc.globally_rejected) return [__('Rejected'), 'red', 'globally_rejected,=,1'];
    return [__(doc.status || 'Discovered'), jobStatusColors[doc.status] || 'gray',
      `status,=,${doc.status || 'Discovered'}`];
  },
};
