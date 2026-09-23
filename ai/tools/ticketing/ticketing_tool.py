from integrations.ticketing.client import TicketingClient


class TicketingTool:

    name = "ticketing"

    def __init__(self):

        self.client = TicketingClient()

    def create_ticket(
        self,
        category,
        description,
        location,
        priority,
    ):

        # Build a useful ticket title
        title = f"{category} - {description}"

        # Include location in the description
        full_description = (
            f"Issue: {description}\n"
            f"Location: {location}\n"
            f"Priority: {priority}"
        )

        result = self.client.create_ticket(

            title=title,

            description=full_description,

            # Currently your API uses ticket type ID 12
            ticket_type_id=12,

            priority=priority,
        )

        return result
    
    def get_my_tickets(self):

        return self.client.get_my_tickets()

    def get_ticket_by_number(self, ticket_number):
        search_result = self.client.search_ticket(ticket_number)

        tickets = search_result.get("content", [])

        if not tickets:
            return None

        ticket_id = tickets[0].get("id")

        if not ticket_id:
            return None

        return self.client.get_ticket_by_id(ticket_id)