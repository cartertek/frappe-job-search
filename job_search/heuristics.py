"""Shared definitions for built-in and custom research heuristics."""

JOB_TITLE_HEURISTIC_ID = 'builtin:job-title'


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
    result.extend({
        'name': row.name, 'heuristic_name': row.heuristic_name,
        'description': getattr(row, 'description', ''),
    } for row in search.heuristics)
    return result
