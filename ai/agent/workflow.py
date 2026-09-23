from ai.agent.conversation import ConversationState
from ai.agent.orchestrator import AgentOrchestrator
from ai.tools.ticketing.ticketing_tool import TicketingTool


class AgentWorkflow:

    def __init__(self, state=None):

        self.orchestrator = AgentOrchestrator()

        self.ticketing = TicketingTool()

        if state is not None:
            self.state = state
        else:
            self.state = ConversationState()

    def handle_ticket_status(self):
        try:
            # Specific ticket requested
            if self.state.ticket_number:

                ticket = self.ticketing.get_ticket_by_number(
                    self.state.ticket_number
                )

                if not ticket:
                    return {
                        "type": "message",
                        "message": f"I couldn't find ticket {self.state.ticket_number}."
                    }

                status = ticket.get("status") or {}
                priority = ticket.get("priority") or {}
                requester = ticket.get("requester") or {}
                assigned_to = ticket.get("assignedTo") or {}

                ticket_number = ticket.get("ticketNumber")
                ticket_query = self.state.ticket_query or "DETAILS"

                # STATUS
                if ticket_query == "STATUS":
                    return {
                        "type": "ticket_answer",
                        "message": (
                            f"Ticket {ticket_number} is currently "
                            f"{status.get('status', 'Unknown')}."
                        ),
                        "answer_type": "STATUS",
                        "ticket": {
                            "ticket_number": ticket_number,
                            "status": status.get("status", "Unknown"),
                            "priority": priority.get("name", "Unknown"),
                            "title": ticket.get("title"),
                            "web_url": ticket.get("webUrl"),
                        }
                    }

                # DETAILS
                if ticket_query == "DETAILS":
                    return {
                        "type": "ticket_detail",
                        "message": "Here are the details of your ticket.",
                        "ticket": {
                            "ticket_number": ticket_number,
                            "title": ticket.get("title"),
                            "description": ticket.get("description"),
                            "status": status.get("status", "Unknown"),
                            "priority": priority.get("name", "Unknown"),
                            "requester": requester.get(
                                "displayName",
                                "Unknown"
                            ),
                            "assigned_to": assigned_to.get(
                                "displayName",
                                "Not assigned"
                            ),
                            "created_at": ticket.get("createdAt"),
                            "web_url": ticket.get("webUrl"),
                        }
                    }

                # ASSIGNED TO
                if ticket_query == "ASSIGNED_TO":
                    assigned_name = assigned_to.get("displayName")

                    if assigned_name:
                        answer = (
                            f"Ticket {ticket_number} is assigned to "
                            f"{assigned_name}."
                        )
                    else:
                        answer = (
                            f"Ticket {ticket_number} is currently "
                            f"not assigned to anyone."
                        )

                    return {
                        "type": "ticket_answer",
                        "message": answer,
                        "answer_type": "ASSIGNED_TO",
                        "ticket": {
                            "ticket_number": ticket_number,
                            "assigned_to": assigned_name or "Not assigned",
                            "status": status.get("status", "Unknown"),
                            "web_url": ticket.get("webUrl"),
                        }
                    }

                # REQUESTER
                if ticket_query == "REQUESTER":
                    requester_name = requester.get(
                        "displayName",
                        "Unknown"
                    )

                    return {
                        "type": "ticket_answer",
                        "message": (
                            f"Ticket {ticket_number} was raised by "
                            f"{requester_name}."
                        ),
                        "answer_type": "REQUESTER",
                        "ticket": {
                            "ticket_number": ticket_number,
                            "requester": requester_name,
                            "web_url": ticket.get("webUrl"),
                        }
                    }

                # CREATED DATE
                if ticket_query == "CREATED_DATE":
                    created_at = ticket.get("createdAt")

                    return {
                        "type": "ticket_answer",
                        "message": (
                            f"Ticket {ticket_number} was created on "
                            f"{created_at}."
                        ),
                        "answer_type": "CREATED_DATE",
                        "ticket": {
                            "ticket_number": ticket_number,
                            "created_at": created_at,
                            "web_url": ticket.get("webUrl"),
                        }
                    }

                # UNKNOWN
                return {
                    "type": "ticket_detail",
                    "message": "Here are the details of your ticket.",
                    "ticket": {
                        "ticket_number": ticket_number,
                        "title": ticket.get("title"),
                        "description": ticket.get("description"),
                        "status": status.get("status", "Unknown"),
                        "priority": priority.get("name", "Unknown"),
                        "requester": requester.get(
                            "displayName",
                            "Unknown"
                        ),
                        "assigned_to": assigned_to.get(
                            "displayName",
                            "Not assigned"
                        ),
                        "created_at": ticket.get("createdAt"),
                        "web_url": ticket.get("webUrl"),
                    }
                }

            # No specific ticket number:
            # Show user's recent tickets
            result = self.ticketing.get_my_tickets()

            tickets = result.get("content", [])

            if not tickets:
                return {
                    "type": "ticket_status",
                    "message": "I couldn't find any tickets for you.",
                    "tickets": []
                }

            ticket_list = []

            for ticket in tickets:
                status = ticket.get("status") or {}
                priority = ticket.get("priority") or {}

                ticket_list.append({
                    "ticket_number": ticket.get("ticketNumber"),
                    "title": ticket.get("title"),
                    "status": status.get("status") or "Unknown",
                    "priority": priority.get("name", "Unknown"),
                })

            return {
                "type": "ticket_status",
                "message": "Here are your recent tickets.",
                "tickets": ticket_list
            }

        except Exception as e:
            print("TICKET STATUS ERROR:", str(e))

            return {
                "type": "error",
                "message": "I couldn't retrieve your ticket status."
            }
    def process_message(self, user_message):

        agent_result = self.orchestrator.understand_request(
            user_message
        )

        self.state.update_from_agent(
            agent_result
        )

        # ==========================================
        # CREATE TICKET
        # ==========================================

        if self.state.intent == "CREATE_TICKET":

            return self.handle_create_ticket()


        # ==========================================
        # CHECK TICKET STATUS
        # ==========================================

        if self.state.intent == "CHECK_TICKET_STATUS":

            return self.handle_ticket_status()


        # ==========================================
        # OTHER
        # ==========================================

        return {
            "type": "message",
            "message": (
                "Hello! 👋 I can help you with Service "
                "Excellence tasks such as creating a ticket "
                "or checking ticket status."
            ),
        }

    def handle_create_ticket(self):

        missing = self.state.get_missing_fields()

        # ----------------------------------------------
        # Ask for missing description
        # ----------------------------------------------

        if "description" in missing:

            self.state.current_question = "description"

            if self.state.category == "Network Issue":

                return {
                    "type": "question",
                    "field": "description",
                    "message": "What network problem are you facing?",
                    "options": [
                        "Internet not working",
                        "Wi-Fi not connecting",
                        "Network is slow",
                        "LAN connection issue",
                        "Other",
                    ],
                }

            if self.state.category == "Desktop Repair":

                return {
                    "type": "question",
                    "field": "description",
                    "message": "What desktop problem are you facing?",
                    "options": [
                        "Desktop not switching on",
                        "Monitor/display issue",
                        "Keyboard or mouse issue",
                        "Other",
                    ],
                }

            if self.state.category == "Software Issue":

                return {
                    "type": "question",
                    "field": "description",
                    "message": "What software problem are you facing?",
                    "options": [
                        "Application not opening",
                        "Application error",
                        "Application is slow",
                        "Other",
                    ],
                }

            return {
                "type": "question",
                "field": "description",
                "message": "What issue are you facing?",
                "options": [
                    "Screen not working",
                    "Laptop not switching on",
                    "Keyboard issue",
                    "Battery/charging issue",
                    "Other",
                ],
            }

        # ----------------------------------------------
        # Ask for missing location
        # ----------------------------------------------

        if "location" in missing:

            self.state.current_question = "location"

            return {
                "type": "question",
                "field": "location",
                "message": "Where are you currently located?",
                "options": [
                    "Ahmedabad Plant",
                    "Noida Plant",
                    "Corporate Office",
                    "Other",
                ],
            }

        # ----------------------------------------------
        # Ask for missing priority
        # ----------------------------------------------

        if "priority" in missing:

            self.state.current_question = "priority"

            return {
                "type": "question",
                "field": "priority",
                "message": "What priority should this ticket have?",
                "options": [
                    "Low",
                    "Medium",
                    "High",
                    "Critical",
                ],
            }

        # ----------------------------------------------
        # All information collected
        # ----------------------------------------------

        self.state.current_question = None

        return {
            "type": "confirmation",
            "message": "Please confirm the ticket details.",
            "ticket": self.state.get_summary(),
            "options": [
                "Confirm & Create Ticket",
                "Cancel",
            ],
        }

    def handle_option(self, option):

        field = self.state.current_question

        if not field:

            return {
                "type": "message",
                "message": "There is no pending question.",
            }

        # Save selected option

        if field == "description":

            self.state.description = option

        elif field == "location":

            self.state.location = option

        elif field == "priority":

            self.state.priority = option

        self.state.current_question = None

        return self.handle_create_ticket()

    def confirm_ticket(self):

        if not self.state.is_complete():

            return {
                "type": "message",
                "message": (
                    "Some ticket information is still missing."
                ),
            }

        result = self.ticketing.create_ticket(

            category=self.state.category,

            description=self.state.description,

            location=self.state.location,

            priority=self.state.priority,
        )

        if result.get("ticketNumber"):

            ticket_number = result["ticketNumber"]

            web_url = result.get("webUrl")

            self.state.reset()

            return {
                "type": "success",
                "message": "Ticket created successfully.",
                "ticket_number": ticket_number,
                "web_url": web_url,
            }

        return {
            "type": "error",
            "message": (
                "The ticket could not be created."
            ),
            "details": result,
        }

    def cancel(self):

        self.state.reset()

        return {
            "type": "message",
            "message": "Ticket creation cancelled.",
        }