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
        email=None,
        phone=None,
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

        elif department == "Admin" and request_type == "Service Request":

            # Admin HO has two different Service Request resolver groups.
            # Route based on the selected category.
            admin_ho_group_mapping = {
                "Business Card": "Admin - HO - SR",
                "Stationery": "Admin - HO - SR",
                "Stationery Request": "Admin - HO - SR",

                "Courier Facility": "Admin_HO_SR",
                "Fleet Management": "Admin_HO_SR",
                "Conference Room Booking": "Admin_HO_SR",
                "Canteen Management": "Admin_HO_SR",
            }

            group_hint = admin_ho_group_mapping.get(category)

        elif department in [
            "Admin",
            "Safety",
            "Security",
            "Branding",
            "HR Department",
            "Insurance",
            "Finance",
            "Compliance & Risk",
            "Projects",
            "Quality management",
            "Strategy",
        ]:
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

        # Build custom fields
        service_custom_fields = {}
        incident_custom_fields = {}

        if request_type == "Service Request":
                    
            target_date_field_keys = {
                11: "neede_by",   # Admin
                16: "needed_by",  # Safety
                6: "needed_by",   # Branding
                52: "need_by",    # HR
                51: "needed_by",  # Finance
                54: "needed_by",  # Insurance
                50: "needed_by",  # Compliance & Risk
                55: "needed_by",  # IT Department
            }

            target_date_key = target_date_field_keys.get(ticket_type_id)

            if target_date_key and target_date:
                service_custom_fields[target_date_key] = target_date

            if ticket_type_id in target_date_field_keys and business_justification:
                service_custom_fields["business_justification"] = business_justification

            # HR Service Request has an additional required Urgency field
            if ticket_type_id == 52 and urgency:
                service_custom_fields["urgency"] = urgency

            # IT Service Request has additional required contact fields
            if ticket_type_id == 55:

                if email:
                    service_custom_fields["Mail_Id"] = email

                if phone:
                    service_custom_fields["Phone_Number"] = phone

                    # Build Incident Request custom fields

        # IT Incident Request (ticket type 56)
        if request_type == "Incident Request" and ticket_type_id == 56:

            if email:
                incident_custom_fields["Mail_Id"] = email

            if phone:
                incident_custom_fields["phone"] = phone

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
                else (
                    incident_custom_fields
                    if (
                        request_type == "Incident Request"
                        and ticket_type_id == 56
                    )
                    else None
                )
            ),
            group_id=group_id,
            category=category,
            subcategory=subcategory,
            location=location,
        )

        return result
                
    def get_my_tickets(
        self,
        requester_email=None,
        include_closed=True,
        status_ids=None,
    ):
        print("Requester Email id: ", requester_email)
        print("Include Closed:", include_closed)
        print("Status IDs:", status_ids)

        return self.client.get_my_tickets(
            requester_email=requester_email,
            include_closed=include_closed,
            status_ids=status_ids,
        )

    def get_all_tickets(
        self,
        include_closed=True,
        status_ids=None,
        size=20,
    ):
        print("Get All Tickets Include Closed:", include_closed)
        print("Get All Tickets Status IDs:", status_ids)

        return self.client.get_all_tickets(
            include_closed=include_closed,
            status_ids=status_ids,
            size=size,
        )

    def get_ticket_by_number(self, ticket_number):

        search_result = self.client.search_ticket(
            ticket_number
        )

        tickets = search_result.get("content", [])

        requested_number = (
            str(ticket_number)
            .strip()
            .upper()
        )

        # Search may match ticket number, title or description.
        # Therefore, never blindly use the first result.
        exact_ticket = None

        for ticket in tickets:

            result_number = (
                str(ticket.get("ticketNumber", ""))
                .strip()
                .upper()
            )

            if result_number == requested_number:
                exact_ticket = ticket
                break

        if not exact_ticket:
            return None

        ticket_id = exact_ticket.get("id")

        if not ticket_id:
            return None

        return self.client.get_ticket_by_id(
            ticket_id
        )

    def search_tickets(
        self,
        search_query,
        include_closed=True,
        status_ids=None,
        size=20,
    ):
        print("Search All Tickets Query:", search_query)
        print(
            "Search All Tickets Include Closed:",
            include_closed,
        )
        print(
            "Search All Tickets Status IDs:",
            status_ids,
        )

        return self.client.search_tickets(
            search_query=search_query,
            include_closed=include_closed,
            status_ids=status_ids,
            size=size,
        )

    def search_my_tickets(
        self,
        search_query,
        requester_email=None,
        include_closed=True,
        status_ids=None,
        size=20,
    ):
        print("Search My Tickets Query:", search_query)
        print("Search My Tickets Status IDs:", status_ids)
        return self.client.search_my_tickets(
            search_query=search_query,
            requester_email=requester_email,
            include_closed=include_closed,
            status_ids=status_ids,
            size=size,
        )