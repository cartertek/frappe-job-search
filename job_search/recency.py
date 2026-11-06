"""Rolling, evidence-based activity windows for Job Search eligibility."""

from calendar import monthrange
from datetime import date, timedelta

try:
    from frappe.utils import nowdate
except ImportError:
    # Pure-Python preflight runs without a Frappe bench.
    def nowdate():
        return date.today().isoformat()


SUPPORTED_UNITS = {"Days": "days", "Weeks": "weeks", "Months": "months", "Years": "years"}


def active_window_start(count, unit, *, as_of=None):
    """Inclusive start of the configured window; no filter when both fields are empty."""
    if count in (None, "", 0, "0") and not unit:
        return None
    if count in (None, "") or unit not in SUPPORTED_UNITS:
        raise ValueError("Active In the Past requires both a number and a valid unit")
    try:
        amount = int(count)
    except (TypeError, ValueError) as exc:
        raise ValueError("Active In the Past number must be a positive integer") from exc
    if amount <= 0 or str(count).strip() not in (str(amount),):
        raise ValueError("Active In the Past number must be a positive integer")
    if as_of is None:
        as_of = nowdate()
    day = as_of if isinstance(as_of, date) else date.fromisoformat(str(as_of)[:10])
    if unit == "Days":
        return day - timedelta(days=amount)
    if unit == "Weeks":
        return day - timedelta(weeks=amount)
    months = amount * (12 if unit == "Years" else 1)
    total_month = day.year * 12 + day.month - 1 - months
    year, month_index = divmod(total_month, 12)
    month = month_index + 1
    return date(year, month, min(day.day, monthrange(year, month)[1]))


def date_in_window(value, since, *, as_of=None):
    """Require evidenced activity within the window, not just an indexed old posting."""
    if since is None:
        return True
    if not value:
        return False
    if as_of is None:
        as_of = nowdate()
    current = as_of if isinstance(as_of, date) else date.fromisoformat(str(as_of)[:10])
    actual = value if isinstance(value, date) else date.fromisoformat(str(value)[:10])
    return since <= actual <= current
