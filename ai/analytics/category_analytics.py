"""Read-only ticket category ranking (call only after workflow authorization).

Category IDs are resolved for each ticket type. Count requests are bounded,
independent and cached briefly; failures are *not* interpreted as zero.
"""
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from django.core.cache import cache
from ai.agent.catalog import CATEGORIES, SUBCATEGORY_REQUEST_TYPES

logger = logging.getLogger(__name__)

TYPE_LABELS = {
    9: "Incident Request", 11: "Service Request",
    53: "Incident Request", 52: "Service Request",
    56: "Incident Request", 55: "Service Request",
}

# Tune conservatively to avoid overloading the internal portal.
MAX_COUNT_WORKERS = 4
COUNT_TTL_SECONDS = 120
CATEGORY_ID_TTL_SECONDS = 3600
REPORT_TTL_SECONDS = 300


def _safe_cache_key(kind, *parts):
    """ASCII-only, whitespace-free key compatible with memcached."""
    identifier = "\x1f".join(str(part) for part in parts)
    digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:32]
    return f"darpan_category_v4_{kind}_{digest}"


def _count(tool, type_id, category_id, include_closed):
    response = tool.get_all_tickets(
        ticket_type_id=type_id,
        category_id=category_id,
        include_closed=include_closed,
        size=1,
    )
    if not isinstance(response, dict) or response.get("totalElements") is None:
        raise ValueError("Ticket count response missing totalElements")
    count = int(response["totalElements"])
    if count < 0:
        raise ValueError("Ticket count must not be negative")
    return count


def _cached_count(tool, type_id, category_id, include_closed, force_refresh=False):
    key = _safe_cache_key("count", type_id, category_id, int(include_closed))
    if not force_refresh:
        value = cache.get(key)
        if value is not None:
            return int(value)
    value = _count(tool, type_id, category_id, include_closed)
    cache.set(key, value, COUNT_TTL_SECONDS)
    return value


def _resolve_category_id(tool, department, type_id, category, candidates):
    key = _safe_cache_key("category_id", department, type_id, category)
    cached = cache.get(key)
    if cached is not None:
        return int(cached)

    last_error = None
    for subcategory in candidates:
        try:
            result = tool.resolve_category_subcategory(
                ticket_type_id=type_id,
                category_name=category,
                subcategory_name=subcategory,
            )
            if not isinstance(result, dict) or result.get("category_id") is None:
                raise ValueError("Resolver did not provide category_id")
            resolved_name = result.get("category_name")
            if resolved_name and str(resolved_name).strip().casefold() != category.strip().casefold():
                raise ValueError("Resolver returned a different category")
            category_id = int(result["category_id"])
            cache.set(key, category_id, CATEGORY_ID_TTL_SECONDS)
            return category_id
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Darpan category resolution failed for department=%r ticket_type=%s "
                "category=%r subcategory=%r: %s: %s",
                department, type_id, category, subcategory,
                type(exc).__name__, exc,
            )
    raise ValueError(
        f"None of {len(candidates)} mapped subcategories resolved; "
        f"last error: {type(last_error).__name__ if last_error else 'Unknown'}"
    )


def get_category_ranking(tool, department, ticket_type_ids, sort_by="total", force_refresh=False):
    """Return category ranking. `force_refresh` bypasses count/report caches.

    Existing callers need no changes; default cache behavior remains enabled.
    The supplied TicketingTool should allow independent concurrent read calls.
    """
    if department not in {"IT Department", "HR Department", "Admin"}:
        raise ValueError("Department not supported for category reporting")
    if sort_by not in {"total", "non_closed"}:
        sort_by = "total"

    type_ids = tuple(int(value) for value in ticket_type_ids)
    key = _safe_cache_key("report", department, sort_by, *type_ids)
    if not force_refresh:
        cached = cache.get(key)
        if cached is not None:
            return cached

    catalog = CATEGORIES.get(department, {})
    mappings = SUBCATEGORY_REQUEST_TYPES.get(department, {})
    rows = []
    unresolved = []
    # Resolve IDs before submitting the independent count requests.
    # Each route has both total and non-closed counts; both must succeed.
    routes = []
    for category, subcategories in catalog.items():
        expected = 0
        for type_id in type_ids:
            label = TYPE_LABELS.get(type_id)
            if not label:
                continue
            candidates = [
                sub for sub in subcategories
                if label in mappings.get(category, {}).get(sub, [])
            ]
            if not candidates:
                continue
            expected += 1
            try:
                category_id = _resolve_category_id(
                    tool, department, type_id, category, candidates
                )
                routes.append((category, label, type_id, category_id))
            except Exception as exc:
                unresolved.append(f"{category} / {label} (type {type_id}): resolution failed")
                logger.warning("Unresolved route %r/%s/%s: %s", department, type_id, category, exc)
        if expected:
            rows.append({
                "category": category, "total": 0, "non_closed": 0,
                "complete": False, "ticket_types": 0, "_expected": expected,
            })

    # Bound outstanding calls; no unbounded thread creation or retries.
    by_category = {row["category"]: row for row in rows}
    outcomes = {}
    if routes:
        with ThreadPoolExecutor(max_workers=min(MAX_COUNT_WORKERS, len(routes) * 2)) as pool:
            futures = {}
            for category, label, type_id, category_id in routes:
                for include_closed in (True, False):
                    future = pool.submit(
                        _cached_count, tool, type_id, category_id,
                        include_closed, force_refresh
                    )
                    futures[future] = (category, label, type_id, include_closed)
            for future in as_completed(futures):
                category, label, type_id, include_closed = futures[future]
                route_key = (category, label, type_id)
                try:
                    outcomes.setdefault(route_key, {})[include_closed] = future.result()
                except Exception:
                    outcomes.setdefault(route_key, {})[include_closed] = None
                    logger.exception(
                        "Darpan category counting failed: department=%r type=%s category=%r include_closed=%s",
                        department, type_id, category, include_closed,
                    )

    route_count = 0
    for category, label, type_id, category_id in routes:
        values = outcomes.get((category, label, type_id), {})
        total = values.get(True)
        non_closed = values.get(False)
        if total is None or non_closed is None:
            unresolved.append(f"{category} / {label} (type {type_id}): counting failed")
            continue
        if non_closed > total:
            unresolved.append(f"{category} / {label} (type {type_id}): inconsistent counts")
            continue
        row = by_category[category]
        row["total"] += total
        row["non_closed"] += non_closed
        row["ticket_types"] += 1
        route_count += 1

    for row in rows:
        row["complete"] = row["ticket_types"] == row.pop("_expected")
    rows.sort(key=lambda row: (-row[sort_by], row["category"].casefold()))
    report = {
        "department": department,
        "sort_by": sort_by,
        "categories": rows,
        "complete": not unresolved,
        "unresolved": unresolved,
        "routes_counted": route_count,
        "categories_counted": len(rows),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": (
            "Incomplete report: some portal categories could not be resolved or counted. "
            "Missing routes are not treated as zero."
            if unresolved else
            "Counts are filtered by portal category ID and ticket type."
        ),
    }
    if not unresolved:
        cache.set(key, report, REPORT_TTL_SECONDS)
    return report
