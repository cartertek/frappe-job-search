"""Consistent, human-readable identifiers for errors and operator messages."""

import frappe


def job_label(job):
    """Show the job title, retaining the identifier only for disambiguation."""
    name = job if isinstance(job, str) else job.name
    title = (frappe.db.get_value('Job', name, 'job_title') if isinstance(job, str)
             else getattr(job, 'job_title', None))
    return f'{title} ({name})' if title and title != name else str(name)


def opportunity_label(opportunity):
    name = opportunity if isinstance(opportunity, str) else opportunity.name
    title = (frappe.db.get_value('Opportunity', name, 'opportunity_name')
             if isinstance(opportunity, str) else getattr(opportunity, 'opportunity_name', None))
    return f'{title} ({name})' if title and title != name else str(name)
