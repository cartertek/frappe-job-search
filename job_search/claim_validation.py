"""Source-date parsing for evidence-based heuristic claims.

A Data field is used because Frappe's required Date field cannot also hold
the explicit "None" sentinel for an undated source (GitHub issue #13).
"""

import re
from datetime import date

UNPUBLISHED_DATE = "None"


def parse_source_date(value):
    """Return a date or None; accept only ISO dates or the literal 'None'.

    Treat empty / null values as *missing*, not as an undated publication.
    """
    if value == UNPUBLISHED_DATE:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Source Date must be YYYY-MM-DD or the literal None")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Source Date must be a real calendar date (YYYY-MM-DD) or None") from exc


def claim_field_errors(row):
    """Check required claim fields independently of active-search cutoff rules."""
    errors = []
    if not (getattr(row, "reasoning", None) or "").strip():
        errors.append("Reasoning is required")
    try:
        parse_source_date(getattr(row, "source_date", None))
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def source_date_matches_search(value, posted_after):
    """Undated sources are valid only for searches without a date cutoff."""
    date_value = parse_source_date(value)
    return not posted_after or (
        date_value is not None
        and date_value >= date.fromisoformat(str(posted_after)[:10])
    )
