"""Shared definitions for built-in and custom research heuristics."""

JOB_TITLE_HEURISTIC_ID = 'builtin:job-title'
COMPENSATION_HEURISTIC_ID = 'builtin:minimum-compensation'


def research_heuristics(search):
    """Return stable-ID heuristic definitions, including configured built-ins."""
    result = []
    titles = [line.strip() for line in (search.title_matches or '').splitlines() if line.strip()]
    if titles:
        result.append({
            'name': JOB_TITLE_HEURISTIC_ID,
            'heuristic_name': 'Job Title',
            'description': (
                'The job title should be similar to one of the titles below and/or the '
                'job description should describe a role matching one of these titles. '
                'Assess the meaning of the role, not an exact text match.\n\n'
                'Titles:\n' + '\n'.join(f'- {title}' for title in titles)
            ),
        })
    if search.salary_min and getattr(search, 'allow_compensation_heuristic', False):
        minimum = str(search.salary_min)
        currency = getattr(search, 'currency', None)
        period = getattr(search, 'compensation_period', None)
        threshold = ' '.join(str(x) for x in (minimum, currency, period) if x)
        result.append({
            'name': COMPENSATION_HEURISTIC_ID,
            'heuristic_name': 'Minimum Compensation',
            'description': (
                'Based on the company size, role, and market, assess whether this job '
                'is expected to offer compensation well above the specified minimum. '
                'Explain the supporting evidence and reasoning.\n\nMinimum compensation: ' + threshold
            ),
        })
    result.extend({
        'name': row.name, 'heuristic_name': row.heuristic_name,
        'description': getattr(row, 'description', ''),
    } for row in search.heuristics)
    return result
