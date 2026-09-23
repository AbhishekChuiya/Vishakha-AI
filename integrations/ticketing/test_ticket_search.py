from integrations.ticketing.client import TicketingClient

client = TicketingClient()

# Step 1: Search ticket number
search_result = client.search_ticket("INCS-061")

tickets = search_result.get("content", [])

if not tickets:
    print("Ticket not found.")
    exit()

ticket = tickets[0]

ticket_id = ticket.get("id")
ticket_number = ticket.get("ticketNumber")

print("\nTICKET FOUND")
print("Ticket Number:", ticket_number)
print("Ticket ID:", ticket_id)

# Step 2: Get full ticket details
details = client.get_ticket_by_id(ticket_id)

print("\nFULL TICKET DETAILS:")
print(details)