"""Lossless version-5 split: historical Job identities and Opportunity lifecycles.

One initial Opportunity per historical Job keeps every former opportunity-link ID
valid across research, decisions, tasks, applications, interviews and transitions.
This migration does NOT group distinct historical pursuits or delete their records.
"""

import frappe

MARKER = 'job_search:opportunity_split_v5'


def migrate_opportunities_v5():
    if frappe.db.get_default(MARKER):
        return
    if not (frappe.db.exists('DocType', 'Job') and
            frappe.db.exists('DocType', 'Opportunity') and
            frappe.db.exists('DocType', 'Opportunity Job')):
        return

    # Copy historical pursuit metadata, preserving IDs, authorship and dates.
    # The Job SQL table retains the legacy lifecycle columns as migration source
    # even though they are no longer exposed by the new Job schema.
    shared = ('name', 'creation', 'modified', 'modified_by', 'owner', 'docstatus', 'idx',
              'organization', 'status', 'active_job_search', 'priority',
              'discovered_on', 'deadline', 'applied_on', 'next_action_on',
              'closure_reason', 'offer_details', 'last_decision', 'last_decision_record',
              'latest_application', 'interview_schedule', 'globally_rejected',
              'rejection_scope', 'rejection_search', 'rejection_reason',
              'research_findings', 'research_recommendation',
              'application_materials_for_review', 'interview_preparation',
              'human_feedback_and_instructions')
    job_cols = set(frappe.db.get_table_columns('Job'))
    opp_cols = set(frappe.db.get_table_columns('Opportunity'))
    missing = set(shared) - job_cols - {'idx'}
    if missing:
        frappe.throw('Cannot migrate Opportunities; missing historical columns: ' + ', '.join(sorted(missing)))
    fields = [f for f in shared if f in job_cols and f in opp_cols]
    select = [f'j.`{f}`' for f in fields]
    if 'rejection_scope' in fields:
        select[fields.index('rejection_scope')] = (
            "CASE WHEN j.rejection_scope='Job Globally' THEN 'Opportunity Globally' "
            "ELSE j.rejection_scope END")
    fields.append('opportunity_name')
    select.append("COALESCE(NULLIF(TRIM(j.job_title), ''), j.name)")
    fields.append('eligibility_status')
    select.append("'Unverified'")
    quoted = ', '.join('`'+f+'`' for f in fields)
    expressions = ', '.join(select)
    frappe.db.sql(f'''
        INSERT INTO `tabOpportunity` ({quoted})
        SELECT {expressions} FROM `tabJob` j
        WHERE NOT EXISTS (SELECT 1 FROM `tabOpportunity` o WHERE o.name=j.name)
    ''')

    # A child-table association rather than a single Link permits multiple
    # distinct opportunities to share a Job when needed.
    for name in frappe.get_all('Job', pluck='name', limit_page_length=100000):
        if not frappe.db.exists('Opportunity', name):
            frappe.throw(f'Missing migrated Opportunity {name}')
        if not frappe.db.exists('Opportunity Job', {'parent': name, 'job': name}):
            frappe.db.sql('''
                INSERT INTO `tabOpportunity Job`
                (name,parent,parenttype,parentfield,idx,job,creation,modified,owner,modified_by,docstatus)
                SELECT %s,j.name,'Opportunity','jobs',1,j.name,j.creation,j.modified,j.owner,j.modified_by,0
                FROM `tabJob` j WHERE j.name=%s
            ''', (frappe.generate_hash(length=10), name))

    # A Search override now links an Opportunity, not a Job. Historical
    # Opportunities deliberately reuse their former Job IDs.
    if 'opportunity' in frappe.db.get_table_columns('Job Search Membership'):
        frappe.db.sql('''
            UPDATE `tabJob Search Membership` SET opportunity=job
            WHERE (opportunity IS NULL OR opportunity='') AND job IS NOT NULL AND job!=''
        ''')
    # Posting snapshots and evidence remain job-specific while retaining their
    # existing Opportunity links. No posting descriptions or IDs are rewritten.
    for dt in ('Job Search Posting', 'Job Search Research', 'Job Search Source'):
        if {'job', 'opportunity'}.issubset(frappe.db.get_table_columns(dt)):
            frappe.db.sql(f'''
                UPDATE `tab{dt}` SET job=opportunity
                WHERE (job IS NULL OR job='') AND opportunity IS NOT NULL AND opportunity!=''
            ''')

    # Old rejection scopes belong to the *pursuit*, now Opportunity. They
    # provide no evidence that an individual Job was unavailable or separately
    # rejected. Preserve those historical scopes on Opportunity and initialize
    # newly independent Job availability as Unknown pending verification.
    frappe.db.sql('''
        UPDATE `tabJob` SET availability_status='Unknown'
        WHERE availability_status IS NULL OR availability_status=''
    ''')
    # Historical Jobs must have a corresponding same-ID Opportunity exactly
    # once, at migration time. Subsequent Jobs may join existing Opportunities.
    unconverted = frappe.db.sql(''' 
        SELECT j.name FROM `tabJob` j LEFT JOIN `tabOpportunity` o ON o.name=j.name
        WHERE o.name IS NULL
    ''',as_list=True)
    if unconverted:
        frappe.throw(f'Historical Jobs missing initial Opportunities: {unconverted}')
    verify_opportunity_migration()
    frappe.db.set_default(MARKER, '1')


def verify_opportunity_migration():
    """Verify every Job's associations and all historical references.

    A *new* Job does not need an Opportunity with the same document ID.
    Only the one-time historical split uses same-ID identity preservation.
    """
    missing = frappe.db.sql('''
        SELECT j.name FROM `tabJob` j LEFT JOIN `tabOpportunity Job` rel
            ON rel.job=j.name AND rel.parenttype='Opportunity'
        WHERE rel.name IS NULL
    ''',as_list=True)
    missing_links = frappe.db.sql('''
        SELECT rel.name FROM `tabOpportunity Job` rel
        LEFT JOIN `tabOpportunity` o ON o.name=rel.parent AND rel.parenttype='Opportunity'
        LEFT JOIN `tabJob` j ON j.name=rel.job
        WHERE o.name IS NULL OR j.name IS NULL OR j.organization != o.organization
    ''',as_list=True)
    orphans = {}
    for dt in ('Job Search Task', 'Job Search Application', 'Job Search Interview',
               'Job Search Decision', 'Job Search Transition', 'Job Search Research',
               'Job Search Posting', 'Job Search Source', 'Job Search Procedure Execution'):
        if 'opportunity' not in frappe.db.get_table_columns(dt):
            continue
        rows = frappe.db.sql(f'''
            SELECT d.name FROM `tab{dt}` d
            LEFT JOIN `tabOpportunity` o ON o.name=d.opportunity
            WHERE d.opportunity IS NOT NULL AND d.opportunity!='' AND o.name IS NULL
        ''', as_list=True)
        if rows:
            orphans[dt] = rows
    if missing or missing_links or orphans:
        frappe.throw(f'Opportunity migration integrity failed: missing={missing}, links={missing_links}, orphans={orphans}')
    return {'jobs': frappe.db.count('Job'), 'opportunities': frappe.db.count('Opportunity'),
            'opportunity_job_links': frappe.db.count('Opportunity Job')}
