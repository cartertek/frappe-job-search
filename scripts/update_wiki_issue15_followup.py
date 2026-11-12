"""Guarded, idempotent correction of Active Job Search wording in the handbook."""

import frappe

ASSISTANT='chatgpt.a01.2428478@gmail.com'


def update():
    if frappe.session.user != ASSISTANT:
        frappe.throw('Wiki updates require the dedicated assistant account')
    changed=[]
    for row in frappe.get_all('Wiki Document',
                              filters={'route':['like','docs/research-handbook/%']},
                              fields=['name','route','owner'],limit_page_length=100):
        doc=frappe.get_doc('Wiki Document',row.name)
        if doc.owner!=ASSISTANT:
            frappe.throw(f'Refusing to overwrite Wiki page with different owner: {doc.route}')
        original=doc.content or ''
        updated=original.replace('Qualification Search','Active Job Search')
        if updated != original:
            doc.content=updated
            doc.save()
            changed.append(doc.route)
    return {'updated_pages':changed,'count':len(changed)}
