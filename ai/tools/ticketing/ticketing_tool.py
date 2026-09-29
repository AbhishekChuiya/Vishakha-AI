from integrations.ticketing.client import TicketingClient
from ai.tools.ticketing.routing import find_route

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
        subcategory=None,
        impact=None,
        request_type=None,
        department=None,
    ):

        # Build a routing hint from the selected category
        # Map chatbot categories to Service Excellence routing groups
        if department == "IT Department":

            infra_categories = [
                "Hardware",
                "Network",
                "Voice Infrastructure Management",
                "Messaging Server",
                "Cloud Services",
            ]

            if category in infra_categories:
                group_hint = "INFRA"
            else:
                group_hint = subcategory or category

        elif department in ["Admin", "Safety", "Security", "Branding"]:
            group_hint = None

        else:
            group_hint = subcategory or category

        # Look up the exact route in the Excel mapping
        route = find_route(
            department=department,
            request_type=request_type,
            location=location,
            group_hint=group_hint,
        )

        ticket_type_id = int(route["ticket id"])
        group_id = int(route["group id"])

        print("\n========== EXCEL ROUTING ==========")
        print("Department:", department)
        print("Request Type:", request_type)
        print("Location:", location)
        print("Group Name:", route["group name"])
        print("Ticket Type ID:", ticket_type_id)
        print("Group ID:", group_id)
        print("==================================\n")

        # Build ticket title
        if subcategory:
            title = f"{category} - {subcategory} - {description}"
        else:
            title = f"{category} - {description}"

        # Build ticket description
        full_description = (
            f"Request Type: {request_type or 'Not specified'}\n"
            f"Department: {department or 'Not specified'}\n"
            f"Category: {category}\n"
            f"Subcategory: {subcategory or 'Not specified'}\n"
            f"Issue: {description}\n"
            f"Location: {location}\n"
            f"Priority: {priority}\n"
            f"Resolver Group: {route['group name']}\n"
            f"Resolver Group ID: {group_id}"
        )

        if request_type == "Incident Request" and impact:
            full_description += f"\nImpact: {impact}"

        # Ticket type is now taken from Excel, not hardcoded
        result = self.client.create_ticket(
            title=title,
            description=full_description,
            ticket_type_id=ticket_type_id,
            priority=priority,
            impact=(impact if request_type == "Incident Request" else None),
            group_id=group_id,
            category=category,
            subcategory=subcategory,
            location=location,
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

    def search_tickets(self, search_query, size=20):
        return self.client.search_tickets(
            search_query=search_query,
            size=size
        )


    def search_my_tickets(self, search_query, size=20):
        return self.client.search_my_tickets(
            search_query=search_query,
            size=size
        )