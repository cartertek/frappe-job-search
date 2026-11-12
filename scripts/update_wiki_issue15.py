"""Convert official Research Handbook to the independent Job / Opportunity model.

Read an exported Frappe Wiki Document JSON array (name/route/owner/content).
This is an explicit, reviewable content transformation; it NEVER writes or logs
into a Frappe session or impersonates an editor. A separate authorized deployment
must save the generated content under the dedicated assistant account.
"""

import argparse
import hashlib
import json
from pathlib import Path

HANDBOOK = 'docs/research-handbook/'


def section(content, heading, replacement):
    prefix = f'## {heading}\n'
    start=content.find(prefix)
    if start<0:
        raise ValueError(f'Missing Wiki handbook section: {heading}')
    boundary=content.find('\n## ',start+len(prefix))
    if boundary<0:
        boundary=len(content)
    return content[:start]+f'## {heading}\n\n{replacement.strip()}\n'+content[boundary:]


def change(page, original):
    s=original
    if page=='start-here':
        anchor='## Full opportunity research task\n'
        if anchor not in s:raise ValueError('start-here missing anchor')
        s=s.replace(anchor,'''## Where information belongs

**Organization** (`Job Search Employer`) is the reusable employer record. **Job** (`Job`) is the particular opening and contains the complete original description, postings, filters/compensation, source dates, heuristic claims, and **Availability** (`Unknown`, `Active`, `Closed`, or independently `Rejected`). **Opportunity** (`Opportunity`) is the organization-level hiring pursuit: normally one per Organization, with multiple linked Jobs; create separate Opportunities for genuinely separate hiring teams or divisions. Opportunity owns research workflow, decisions, applications, interviews, offers, tasks, and scoped rejection. A single Opportunity may qualify for multiple Job Searches. A rejected Job becomes invalid without rejecting its Opportunity.

'''+anchor,1)
        s=section(s,'Job workflow and review status','''The **Opportunity** progression is **Discovered → Researching → Ready to Review → Qualified → Applied → Interviewing → Accepted**, with **Rejected** for a globally rejected pursuit. These are not Job statuses. Jobs have a separate availability lifecycle. An Opportunity needs **at least one currently Active, qualifying Job** for the selected **Qualification Search** before Ready to Review. An applicant's role-specific evidence belongs on the Job; the pursuit and human authorization belong on the Opportunity. See [Qualification and Prioritization](/docs/research-handbook/qualification-and-prioritization). Research dispositions are not Frappe workflow statuses.''')
        s=section(s,'Completion of in-progress research','''For a given Job Search, resolve researched **Opportunities** by either excluding/rejecting those that fail or moving eligible Opportunities to **Ready to Review** after verifying at least one associated Job. Choose the proper rejection scope: **Search Only** excludes this Opportunity from the current Search without globally rejecting the pursuit; **Opportunity Globally** rejects that pursuit; **Entire Organization** rejects the Organization. A Job may separately be rejected and made invalid. Do not leave completed research perpetually in Researching, fabricate a current opening, or send unsuitable Opportunities for human approval. Only the actual human approver can issue Pursue, application, or offer authorization.''')
        s=s.replace('**before** moving a Job to Ready to Review','**before** moving its Opportunity to Ready to Review')
    elif page=='qualification-and-prioritization':
        s=section(s,'From research to Job status','''The **Opportunity**, not an individual Job, owns **Discovered → Researching → Ready to Review → Qualified → Applied → Interviewing → Accepted**. To advance from Researching to Ready to Review, set its **Qualification Search** and ensure **at least one associated Job** is confirmed Active, satisfies all deterministic Search filters, has its complete original description and a captured Posting, and has all required dated and sourced heuristic claims. A Search must be enabled; the Opportunity and Organization must not be globally rejected, and the Opportunity must not be excluded from the Search. Where explicit heuristic approval is required, the Search needs an Include override targeting the **Opportunity**. Include overrides do **not** bypass readiness requirements. Other Jobs may share evidence only if it genuinely applies to their specific opening.

Only an actual human **Pursue** decision with rationale, cited Opportunity research, and a completed procedure permits **Ready to Review → Qualified** (or an authorized exception where supported). **Needs Research** returns an Opportunity to Researching. **Qualified → Applied** requires a human-authorized confirmed Opportunity application and materials, **Applied → Interviewing** needs an Opportunity interview, and **Interviewing → Accepted** requires offer details and a real human Accept Offer decision.

**Reject From** on the Opportunity supports **Search Only** (exclude from one Search without changing the shared Opportunity pursuit stage), **Opportunity Globally** (reject the pursuit), and **Entire Organization** (globally reject the Organization). Separately rejecting a **Job** sets its availability to Rejected and makes that Job invalid; it does not reject the Opportunity or Organization. Reopening an independently rejected Job restores **Unknown**, not an unsupported claim that it is Active. An Opportunity whose last valid Job becomes invalid loses current eligibility; preserve historical stage transitions and human decisions. Never impersonate the human approver.''')
        s=section(s,'Agent research completion','''For every researched **Opportunity** in a selected Search, either (a) apply a reasoned Search-only exclusion / appropriate broader rejection when it is unsuitable, or (b) move it to **Ready to Review** when at least one linked Job satisfies the qualification gate. If one Job is invalid but another qualifying Job exists, continue evaluating the Opportunity rather than rejecting the whole Organization. A working disposition such as Research further or Deprioritized is not a completed workflow outcome. Agents may reject during research without a human Decline decision; moving the Opportunity beyond Ready to Review still requires actual human approval.''')
    elif page=='opportunity-research':
        s=s.replace('''8. **Complete every in-progress Job.** Reject researched opportunities that fail this search and record the evidence, rejection rationale, and appropriate scope; move those that pass the search and the review-readiness gate to **Ready to Review**. Do not leave completed investigations in Researching. Prepare links and evidence for the review-ready jobs.''','''8. **Complete each researched Opportunity.** For a Search, exclude unsuitable Opportunities from that Search (or reject them globally / by Organization when warranted); do not reject an entire Opportunity just because one Job is invalid and another is still promising. Link each suitable Job to its Opportunity and advance the **Opportunity** to **Ready to Review** only after one Job passes every qualification gate. Do not leave completed investigations in Researching. Prepare supporting Job, posting and research links for the reviewer.''')
        s=s.replace('Jobs sent to Ready to Review','Opportunities sent to Ready to Review')
        s=section(s,'Workflow status handoff','''Before requesting **Ready to Review** on an **Opportunity**, identify a currently valid **Job** linked in the Opportunity's **Jobs** table. Verify that the full employer-published description (not a summary) is saved on that Job and in the captured Job Posting, that the original and Last Active Dates are independently evidenced, and that Job Availability is **Active**. Then set the Opportunity's **Qualification Search** and complete the **Heuristic Claims** on the qualifying Job (exact quotes, nonblank reasoning, source URLs, dated evidence relevant to that particular opening). Validate that the Job meets every deterministic filter and that any required explicit Include is recorded for the Opportunity. A matching search result does not replace the Ready-to-Review gate; an Include override does not bypass it. If no Job qualifies, keep researching the Opportunity and preserve the evidence; do not fabricate an Active opening.

A **Ready-to-Review Opportunity** is not human **Qualified** until the actual human approver records Pursue with rationale and cited research and completed procedure are present. Needs Research returns the Opportunity to Researching. Subsequent Applied / Interviewing / Accepted stages require respectively an authorized saved Opportunity application, an Opportunity interview, and offer details plus human Accept Offer authorization. These pursuit statuses, tasks, interviews and applications must not be written to individual Jobs.''')
        s=section(s,'Completion requirement','''An investigation for a specific Search is complete when the Opportunity is either **excluded from that Search with rationale**, **rejected globally or by Organization when appropriate**, or **Ready to Review** based on at least one valid linked Job. Search-only exclusion **does not** set the shared Opportunity pursuit status to Rejected or affect other Searches. An independently rejected Job is invalid but need not end its Opportunity if other Jobs remain relevant. Agents may reject/exclude and complete research handoff; only humans can authorize Pursue, applications and offers. Retain sources and historical decisions.''')
    elif page=='research-records-and-quality':
        s=section(s,'Research completion and rejection records','''Complete each **Opportunity** investigation for the selected Search by either a reasoned Search-only exclusion / justified Opportunity-global or Organization-wide rejection, or advancement to Ready to Review based on at least one verified Active qualifying Job. Search-only rejection excludes only that Search and does not set the shared Opportunity's pursuit Status to Rejected. Independent Job rejection marks the Job invalid and does not reject its Organization or Opportunity. Save the rationale, source-backed evidence and actual signed-in operator identity. Agents do not create human approval decisions; human Pursue authorization is reserved for moving the Opportunity from Ready to Review to Qualified.''')
        s=section(s,'Job field names for agent records','''Keep **Job**-specific facts and original evidence on `Job`: **Job Description** (`job_description`), full original Posting (`latest_posting`), **Heuristic Claims** (`research_heuristics`), last supported active date and source, location, compensation, employment type, work arrangement, and **Availability** (`availability_status`). Rejection of an individual Job uses `job_rejection_reason`. Keep **Opportunity** pursuit research and human-review summaries on `Opportunity`: **Research Findings & Sources** (`research_findings`), **Agent Recommendation** (`research_recommendation`), **Application Materials for Review** (`application_materials_for_review`), **Interview Preparation** (`interview_preparation`), and **Human Feedback / Instructions** (`human_feedback_and_instructions`). Do not write into historical `*_digest`, `application_review`, `interview_brief`, or legacy lifecycle columns. Save organization-wide facts to Organization, not arbitrary Jobs.''')
        s=s.replace('`Job Search Opportunity.job_description`','`Job.job_description`')
        s=s.replace('**Ready-to-Review handoff gate:** Do not move a Job to **Ready to Review**','**Ready-to-Review handoff gate:** Do not move an Opportunity to **Ready to Review**')
        s=s.replace('**Keep analysis separate.** Put eligibility checks, research observations, contradictions, citations and summaries in **Research Findings & Sources**','**Keep analysis separate.** Put Opportunity-level eligibility conclusions, research observations, contradictions, citations and summaries in **Research Findings & Sources**')
        s=s.replace('**manual researcher quality gate**, in addition to the app\'s currently enforced workflow/heuristic validation; do not assume the server checks description completeness.','**manual researcher quality gate**, alongside the server\'s check that a captured Job Posting and nonempty Job Description exist. Verify actual completeness yourself; the server cannot independently prove that all source sections were captured.')
        s=s.replace('in Research Findings, not in a legacy claim field','in Opportunity Research Findings, not in a legacy Job claim field')
    elif page=='evidence-standards':
        anchor='## Historical validity versus current status\n'
        if anchor not in s:raise ValueError('evidence standards missing anchor')
        s=s.replace(anchor,'''## Evidence storage and availability

The **Job** is the record for a specific vacancy and its original description, Posting snapshots, recency, qualification facts and independent **Availability** (`Unknown`, `Active`, `Closed`, or `Rejected`). A Posting describes the state of one observed listing; a currently reachable webpage is not, by itself, proof of active hiring. Verify the specific opening before marking its Job Active. **Opportunity** is the surrounding Organization hiring pursuit and may include more than one Job. Rejected/Closed Jobs cannot qualify an Opportunity, but other genuinely qualifying Jobs may. The Opportunity retains its human pursuit status and historical decisions separately from the changing Job availability.

'''+anchor,1)
    elif page=='discovery-methods':
        anchor='## Strategy-led batching and inexpensive screening\n'
        if anchor not in s:raise ValueError('discovery methods missing anchor')
        s=s.replace(anchor,'''## Reuse of Jobs and Opportunities

Deduplicate **Jobs** by concrete requisition and source evidence. Reuse the existing **Opportunity** for the Organization by default; open a second only when a distinct hiring team/division or separate recruiting effort is evidenced. Link multiple Jobs to one Opportunity rather than fabricating duplicate pursuits. A Job may be associated with multiple Opportunities when actually justified. A Job Search matches an Opportunity based on its associated Jobs; per-Search exclusions apply to the Opportunity, while independently rejected Jobs remain invalid for qualification.

'''+anchor,1)
    elif page=='contact-research':
        anchor='## Evidence grades (working framework, not measured probabilities)\n'
        if anchor not in s:raise ValueError('contact research missing anchor')
        s=s.replace(anchor,'''## Relationship to the Opportunity

A private contact pathway is often **Job-specific**: evidence must link a person to the particular opening and must not be automatically transferred to unrelated Jobs. Store the cited quote, source and date on the relevant Job heuristic claim; store the broader recruiting relationship and pursuit history on the **Opportunity**. When several Jobs belong to one hiring team, verify what each contact invitation actually covers before reusing it. A conversation's research evidence does not authorize outreach or an application; those decisions belong to the human-controlled Opportunity workflow.

'''+anchor,1)
    else:raise ValueError('Unexpected research handbook route: '+page)
    # Reject leftover obsolete statements that would contradict the new schema.
    obsolete=('Job Globally','Job Search Opportunity.job_description','Job status progression','The Job has one Status field','the Job status to Rejected without globally')
    residual=[phrase for phrase in obsolete if phrase in s]
    if residual:
        raise ValueError(f'{page}: obsolete handbook content remained: {residual}')
    return s


def convert(documents):
    converted=[]
    for row in documents:
        if not row['route'].startswith(HANDBOOK):
            raise ValueError('Refusing to modify non-handbook Wiki Document')
        page=row['route'].removeprefix(HANDBOOK)
        updated=change(page,row['content'])
        if updated==row['content']:
            raise ValueError('Wiki handbook page unchanged: '+page)
        converted.append({**row,'original_sha256':hashlib.sha256(row['content'].encode('utf-8')).hexdigest(),'content':updated})
    return converted


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=Path)
    parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    documents=json.loads(args.source.read_text())
    rewritten=convert(documents)
    args.destination.write_text(json.dumps(rewritten,ensure_ascii=False,indent=2)+'\n')
    for before,after in zip(documents,rewritten):
        print(after['route'],len(before['content']),'->',len(after['content']))

if __name__=='__main__':main()
