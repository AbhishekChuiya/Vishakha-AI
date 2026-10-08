"""Read-only category rankings; only call behind AgentWorkflow's analytics permission check.

Counts combine distinct category IDs under each applicable portal ticket type.
A report with unresolved routes is explicitly marked incomplete.
"""
from datetime import datetime, timezone
from django.core.cache import cache
from ai.agent.catalog import CATEGORIES, SUBCATEGORY_REQUEST_TYPES

TYPE_LABELS = {
    9: "Incident Request", 11: "Service Request", 53: "Incident Request",
    52: "Service Request", 56: "Incident Request", 55: "Service Request",
}


def _count(tool, type_id, category_id, include_closed):
    response = tool.get_all_tickets(ticket_type_id=type_id, category_id=category_id,
                                    include_closed=include_closed, size=1)
    count = response.get("totalElements")
    if count is None:
        raise ValueError("Ticket count response missing totalElements")
    return int(count)


def get_category_ranking(tool, department, ticket_type_ids, sort_by="total"):
    if department not in {"IT Department", "HR Department", "Admin"}:
        raise ValueError("Department not supported for category reporting")
    if sort_by not in {"total", "non_closed"}:
        sort_by = "total"
    cache_key = f"darpan:categories:v2:{department}:{sort_by}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    catalog = CATEGORIES.get(department, {})
    mappings = SUBCATEGORY_REQUEST_TYPES.get(department, {})
    rows = []
    unresolved = []
    route_count = 0
    # Full department catalog: no sampling or silently omitted categories.
    for category, subcategories in catalog.items():
        total = 0
        non_closed = 0
        covered = 0
        expected_types = []
        for type_id in ticket_type_ids:
            label = TYPE_LABELS.get(type_id)
            if not label:
                continue
            # Choose a real allowed subcategory for each type. IDs can vary by type.
            candidates = [sub for sub in subcategories if label in
                          mappings.get(category, {}).get(sub, [])]
            if not candidates:
                continue
            expected_types.append(type_id)
            route_key = f"darpan:category-id:v2:{department}:{type_id}:{category}"
            category_id = cache.get(route_key)
            if category_id is None:
                try:
                    resolved = tool.resolve_category_subcategory(
                        ticket_type_id=type_id, category_name=category,
                        subcategory_name=candidates[0],
                    )
                    category_id = int(resolved["category_id"])
                    cache.set(route_key, category_id, 3600)
                except Exception as exc:
                    unresolved.append(f"{category} / {label}: resolution failed ({type(exc).__name__})")
                    continue
            try:
                all_count = _count(tool, type_id, category_id, True)
                active_count = _count(tool, type_id, category_id, False)
            except Exception as exc:
                unresolved.append(f"{category} / {label}: count failed ({type(exc).__name__})")
                continue
            total += all_count
            non_closed += active_count
            covered += 1
            route_count += 1
        if expected_types:
            rows.append({"category": category, "total": total, "non_closed": non_closed,
                         "complete": covered == len(expected_types),
                         "ticket_types": covered})
    rows.sort(key=lambda x: (-x[sort_by], x["category"].casefold()))
    report = {
        "department": department, "sort_by": sort_by, "categories": rows,
        "complete": not unresolved, "unresolved": unresolved,
        "routes_counted": route_count, "categories_counted": len(rows),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": ("Ranking is incomplete because some portal categories could not be resolved or counted. "
                 "Missing routes are not treated as zero."
                 if unresolved else "Counts are filtered by portal category ID and ticket type."),
    }
    # Don't cache incomplete reports; transient failures must be retried.
    if not unresolved:
        cache.set(cache_key, report, 300)
    return report
