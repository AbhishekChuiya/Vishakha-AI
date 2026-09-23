from integrations.ticketing.client import TicketingClient


client = TicketingClient()

result = client.get_my_tickets()

print("\nTICKET STATUS API RESPONSE:")
print(result)