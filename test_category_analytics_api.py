"""Read-only smoke test. Run: python manage.py shell < test_category_analytics_api.py"""
from ai.agent.catalog import CATEGORIES, SUBCATEGORY_REQUEST_TYPES
from ai.tools.ticketing.ticketing_tool import TicketingTool

DEPARTMENT = "IT Department"
TICKET_TYPES = {"Incident Request": 56, "Service Request": 55}

tool = TicketingTool()
print("\n=== DARPAN CATEGORY FILTER READ-ONLY TEST ===")
print("Department:", DEPARTMENT)

tested = 0
for category, subcategories in CATEGORIES.get(DEPARTMENT, {}).items():
    for subcategory in subcategories:
        allowed = SUBCATEGORY_REQUEST_TYPES.get(DEPARTMENT, {}).get(category, {}).get(subcategory, [])
        for request_type in allowed:
            type_id = TICKET_TYPES.get(request_type)
            if type_id is None:
                continue
            print("\nTesting:", category, "/", subcategory, "/", request_type, "type", type_id)
            try:
                resolved = tool.resolve_category_subcategory(
                    ticket_type_id=type_id,
                    category_name=category,
                    subcategory_name=subcategory,
                )
                print("Resolved IDs:", resolved)
                category_id = resolved.get("category_id")
                if category_id is None:
                    print("WARNING: category_id not returned")
                    continue
                result = tool.get_all_tickets(ticket_type_id=type_id, category_id=category_id, size=1)
                print("Category total:", result.get("totalElements"))
                result_open = tool.get_all_tickets(ticket_type_id=type_id, category_id=category_id,
                                                   include_closed=False, size=1)
                print("Category non-closed:", result_open.get("totalElements"))
                tested += 1
            except Exception as error:
                print("ERROR:", type(error).__name__, str(error)[:300])
            if tested >= 2:
                break
        if tested >= 2:
            break
    if tested >= 2:
        break
print("\nSuccessful category routes tested:", tested)
print("Note: This verifies category filtering, NOT a complete category ranking.")
