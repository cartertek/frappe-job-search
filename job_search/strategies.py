"""Research strategy ordering for an individual Job Search."""

from job_search.permissions import require_doc, require_operator


def ordered_strategies(search):
    """Return assigned strategy documents with effective priorities, sorted first to last.

    An unset or zero override inherits the strategy default. Ties preserve assignment
    order (and then a stable strategy ID), avoiding nondeterministic agent workflows.
    """
    result = []
    for row in (search.research_strategies or []):
        strategy = require_doc("Job Search Research Strategy", row.research_strategy, "read")
        default = int(strategy.default_priority)
        effective = int(row.priority_override or default)
        result.append({
            "strategy": strategy.name,
            "strategy_name": strategy.strategy_name,
            "instructions": strategy.description,
            "default_priority": default,
            "priority_override": int(row.priority_override or 0),
            "effective_priority": effective,
            "assignment_order": row.idx,
        })
    return sorted(result, key=lambda x: (x["effective_priority"], x["assignment_order"], x["strategy"]))


def get_search_strategies(search_name):
    require_operator()
    return ordered_strategies(require_doc("Job Search Search", search_name, "read"))
