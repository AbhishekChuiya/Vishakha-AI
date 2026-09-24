from integrations.ticketing.client import TicketingClient


client = TicketingClient()

queries = [
    "laptop",
    "network",
    "screen",
    "keyboard",
]

for query in queries:
    print("\n" + "=" * 70)
    print("SEARCH:", query)

    result = client.search_tickets(query)

    print("RESULT:")
    print(result)