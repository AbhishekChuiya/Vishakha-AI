from integrations.ticketing.client import TicketingClient


client = TicketingClient()

print("=" * 70)
print("TEST: SEARCH + REQUESTER EMAIL")
print("=" * 70)

search_query = "laptop"
requester_email = client.requester

print("Search:", search_query)
print("Requester:", requester_email)
print()

try:
    result = client.search_tickets(
        search_query=search_query,
        size=20
    )

    print("GLOBAL SEARCH")
    print("-" * 70)
    print("Total:", result.get("totalElements"))

    for ticket in result.get("content", []):
        print(
            ticket.get("ticketNumber"),
            "|",
            ticket.get("title")
        )

except Exception as e:
    print("GLOBAL SEARCH ERROR:", e)


print()
print("=" * 70)
print("TESTING REQUESTER FILTER DIRECTLY")
print("=" * 70)

try:
    import requests

    url = f"{client.base_url}/api/itsm/v1/tickets"

    headers = {
        "Authorization": f"Bearer {client.pat}",
        "Accept": "application/json",
    }

    params = {
        "search": search_query,
        "requesterEmail": requester_email,
        "includeClosed": "true",
        "size": 20,
        "sort": "createdDate,desc",
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30,
    )

    print("HTTP STATUS:", response.status_code)
    print("REQUEST URL:")
    print(response.url)
    print()

    response.raise_for_status()

    result = response.json()

    print("FILTERED SEARCH")
    print("-" * 70)
    print("Total:", result.get("totalElements"))

    for ticket in result.get("content", []):
        print(
            ticket.get("ticketNumber"),
            "|",
            ticket.get("title"),
            "| requester:",
            ticket.get("requester")
        )

except Exception as e:
    print("FILTERED SEARCH ERROR:", e)