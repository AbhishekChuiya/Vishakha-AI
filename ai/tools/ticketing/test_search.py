from ai.tools.ticketing.ticketing_tool import TicketingTool


tool = TicketingTool()

queries = [
    "laptop",
    "network",
    "screen",
    "keyboard",
]

for query in queries:
    print("\n" + "=" * 70)
    print("SEARCH:", query)

    result = tool.search_tickets(query)

    tickets = result.get("content", [])

    print("TOTAL:", result.get("totalElements"))
    print("RETURNED:", len(tickets))

    for ticket in tickets[:5]:
        print(
            ticket.get("ticketNumber"),
            "|",
            ticket.get("title"),
            "|",
            (ticket.get("status") or {}).get("status"),
            "|",
            (ticket.get("priority") or {}).get("name"),
        )