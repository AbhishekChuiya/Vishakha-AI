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
        start_date=None,
        target_date=None,
        business_justification=None,
        urgency=None,
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

        elif department in ["Admin", "Safety", "Security", "Branding", "HR Department", "Insurance", "Finance", "Compliance & Risk", "Projects", "Quality management", "Strategy"]:
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

        # Build Service Request custom fields based on the actual ticket type
        service_custom_fields = {}

        if request_type == "Service Request":

            target_date_field_keys = {
                11: "neede_by",   # Admin
                16: "needed_by",  # Safety
                6: "needed_by",   # Branding
                52: "need_by",    # HR
                51: "needed_by",  # Finance
                54: "needed_by",  # Insurance
                50: "needed_by",  # Compliance & Risk
            }

            target_date_key = target_date_field_keys.get(ticket_type_id)

            if target_date_key and target_date:
                service_custom_fields[target_date_key] = target_date

            if ticket_type_id in target_date_field_keys and business_justification:
                service_custom_fields["business_justification"] = business_justification

            # HR Service Request has an additional required Urgency field
            if ticket_type_id == 52 and urgency:
                service_custom_fields["urgency"] = urgency

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

        if request_type == "Incident Request":
            if impact:
                full_description += f"\nImpact: {impact}"

            if start_date:
                full_description += f"\nWhen did this start?: {start_date}" 

        # Ticket type is now taken from Excel, not hardcoded
        result = self.client.create_ticket(
            title=title,
            description=full_description,
            ticket_type_id=ticket_type_id,
            priority=priority,
            impact=(impact if request_type == "Incident Request" else None),
            start_date=(
                start_date
                if request_type == "Incident Request"
                else None
            ),
            custom_fields=(
                service_custom_fields
                if request_type == "Service Request"
                else None
            ),
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