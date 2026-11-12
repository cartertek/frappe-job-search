"""Apply a reviewed issue-15 Wiki handbook export to a Frappe site.

Requires an active Frappe session under the dedicated assistant account, and
matches the original Wiki content hash before any writes. Fails closed on
unexpected records or user edits. A real document.save() preserves audit trail.
"""

import hashlib
import json
from pathlib import Path

ASSISTANT = 'chatgpt.a01.2428478@gmail.com'


def apply(document_json):
    import frappe

    if frappe.session.user != ASSISTANT:
        frappe.throw('Use the dedicated assistant Frappe account; do not impersonate anyone')
    items=json.loads(Path(document_json).read_text())
    changes=[]
    for item in items:
        if not item['route'].startswith('docs/research-handbook/'):
            frappe.throw('Refusing to edit a page outside Research Handbook')
        doc=frappe.get_doc('Wiki Document',item['name'])
        if doc.route!=item['route'] or doc.owner!=ASSISTANT:
            frappe.throw(f'Unexpected Wiki Document owner or route: {item["route"]}')
        current=hashlib.sha256((doc.content or '').encode('utf-8')).hexdigest()
        intended=hashlib.sha256(item['content'].encode('utf-8')).hexdigest()
        if current==intended:
            print('Already updated:',doc.route)
            continue
        if current!=item['original_sha256']:
            frappe.throw(f'Wiki Document changed since review; update aborted: {doc.route}')
        changes.append((doc,item['content']))
    for doc,new_content in changes:
        doc.content=new_content
        doc.save()
        print('Updated Wiki handbook:',doc.route)
    return {'pages_reviewed':len(items),'pages_updated':len(changes)}


def main():
    import argparse
    import frappe

    p=argparse.ArgumentParser()
    p.add_argument('site')
    p.add_argument('wiki_json')
    p.add_argument('--sites-path',default=None)
    args=p.parse_args()
    frappe.init(site=args.site,sites_path=args.sites_path)
    frappe.connect(set_admin_as_user=False)
    frappe.set_user(ASSISTANT)
    try:
        print(apply(args.wiki_json))
        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise
    finally:
        frappe.destroy()

if __name__=='__main__':main()
