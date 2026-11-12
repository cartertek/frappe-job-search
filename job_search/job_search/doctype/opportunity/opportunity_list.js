frappe.listview_settings['Opportunity'] = {add_fields:['status','eligibility_status'],
  get_indicator(doc) {
    const colors={Discovered:'gray',Researching:'orange','Ready to Review':'blue',
      Qualified:'green',Applied:'blue',Interviewing:'purple',Accepted:'green',Rejected:'red'};
    return [__(doc.status||'Discovered'),colors[doc.status]||'gray','status,=,'+doc.status];
  }};
