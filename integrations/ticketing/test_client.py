from integrations.ticketing.client import TicketingClient


client = TicketingClient()


result = client.create_ticket(

    title="Darpan AI Test Ticket",

    description=(
        "This ticket was created "
        "from the Darpan AI Employee Assistant."
    ),

    ticket_type_id=12,

    priority="High",
)


print("\nTICKETING API RESPONSE:")
print(result)