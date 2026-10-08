from ai.agent.conversation import ConversationState
from ai.agent.orchestrator import AgentOrchestrator
from ai.tools.ticketing.ticketing_tool import TicketingTool
from ai.tools.ticketing.routing import get_departments
from ai.agent.config import REQUEST_TYPES, LOCATIONS
from ai.agent.catalog import CATEGORIES, SUBCATEGORY_REQUEST_TYPES, find_catalog_item
from datetime import datetime, timedelta
from django.utils import timezone
from ai.agent.ticket_statuses import TICKET_STATUS_IDS
# --------------------------------------------------
# TICKET SEARCH DEPARTMENT CONFIGURATION
# --------------------------------------------------

DEPARTMENT_SEARCH_CONFIG = {
    "Admin": {
        "ticket_type_ids": [9, 11],
    },

    "Branding": {
        "ticket_type_ids": [14, 7, 6],
    },

    "Compliance & Risk": {
        "ticket_type_ids": [50],
    },

    "Finance": {
        "ticket_type_ids": [51],
    },

    "HR Department": {
        "ticket_type_ids": [53, 52],
    },

    "IT Department": {
        "ticket_type_ids": [56, 55],
    },

    "Insurance": {
        "ticket_type_ids": [54],
    },

    "Projects": {
        "ticket_type_ids": [59],
    },

    "Quality management": {
        "ticket_type_ids": [61],
    },

    "Safety": {
        "ticket_type_ids": [12, 16],
    },

    "Security": {
        "ticket_type_ids": [8],
    },

    "Strategy": {
        "ticket_type_ids": [60],
    },
}

TICKET_TYPE_NAMES = {
    6: "Service Request",
    7: "Request For Information",
    8: "Incident Request",
    9: "Incident Request",
    11: "Service Request",
    12: "Incident Request",
    14: "Change Management",
    16: "Service Request",
    50: "Service Request",
    51: "Service Request",
    52: "Service Request",
    53: "Incident Request",
    54: "Service Request",
    55: "Service Request",
    56: "Incident Request",
    59: "Change Management",
    60: "Service Request",
    61: "Customer Complaint",
}

class AgentWorkflow:

    def __init__(
        self,
        state=None,
        requester_email=None,
        actor_email=None,
    ):

        self.orchestrator = AgentOrchestrator()

        self.ticketing = TicketingTool()

        self.requester_email = requester_email

        self.actor_email = actor_email

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
            result = self.ticketing.get_my_tickets(
                requester_email=self.requester_email
            )

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
                
    def process_message(self, user_message, chat_id=None):

        # ----------------------------------------------
        # HANDLE ANSWER TO CURRENT QUESTION
        # ----------------------------------------------

        if self.state.current_question:
            return self.handle_option(user_message)

        agent_result = self.orchestrator.understand_request(
            user_message,
            current_ticket_number=self.state.ticket_number,
            chat_id=chat_id
        )

        # Analytics is a stateless read-only operation. Do not modify the
        # conversation's ticket-creation state or require new state fields.
        if agent_result.get("intent") == "ANALYZE_TICKETS":
            return self.handle_ticket_analytics(agent_result)

        self.state.update_from_agent(agent_result)

        # CREATE TICKET
        if self.state.intent == "CREATE_TICKET":
            return self.handle_create_ticket()

        # CHECK TICKET STATUS
        if self.state.intent == "CHECK_TICKET_STATUS":
            return self.handle_ticket_status()

        if self.state.intent == "SEARCH_TICKETS":
            return self.handle_search_tickets()

        return {
            "type": "message",
            "message": (
                "Hello! 👋 I can help you with Service "
                "Excellence tasks such as creating a ticket "
                "or checking ticket status."
            ),
        }

    def handle_ticket_analytics(self, agent_result):
        """Authorized IT summary only; never return department-wide data
        to arbitrary employees or fall back to unrestricted ticket searches.
        """
        from django.conf import settings

        if agent_result.get("analytics_department") != "IT Department":
            return {"type": "message", "message": "That analytics report is not available yet."}

        # Deny access by default. Configure explicit approved employees in
        # Django settings; an authenticated email alone is not authorization.
        approved = getattr(settings, "DARPAN_ANALYTICS_ALLOWED_EMAILS", ())
        if isinstance(approved, str):
            approved = [part.strip() for part in approved.split(",")]
        approved = {str(email).strip().casefold() for email in approved if email}
        actor = str(self.requester_email or "").strip().casefold()

        if not actor or actor not in approved:
            return {
                "type": "message",
                "message": "You don't have permission to view department-wide ticket analytics.",
            }

        try:
            from ai.analytics.ticket_analytics import TicketAnalytics
            data = TicketAnalytics().get_it_summary()
            if data.get("department") != "IT Department":
                raise ValueError("Unexpected analytics department")
            for key in ("total_tickets", "open_tickets", "resolved_tickets",
                        "closed_tickets", "cancelled_tickets"):
                if key not in data:
                    raise ValueError(f"Analytics response missing {key}")
            breakdown = data.get("by_request_type") or {}
            incident = breakdown.get("Incident Request", {})
            service = breakdown.get("Service Request", {})
            summary = (
                "IT Department Ticket Summary\n"
                f"Total: {data['total_tickets']}\n"
                f"Open (API non-closed filter): {data['open_tickets']}\n"
                f"Resolved: {data['resolved_tickets']}\n"
                f"Closed: {data['closed_tickets']}\n"
                f"Cancelled: {data['cancelled_tickets']}\n\n"
                f"Incident Requests: {incident.get('total', 'Unavailable')}\n"
                f"Service Requests: {service.get('total', 'Unavailable')}"
            )
            return {
                "type": "message",  # Compatible with existing chatbot UI
                "message": summary,
            }
        except Exception as exc:
            # Don't leak tokens, requests or internal stack traces to employees.
            print("TICKET ANALYTICS ERROR:", type(exc).__name__)
            return {
                "type": "message",
                "message": "I couldn't retrieve the ticket analytics right now.",
            }

    def handle_create_ticket(self):
        
        # ----------------------------------------------
        # STEP 0: Department
        # ----------------------------------------------

        department = self.normalize_department(
            self.state.department
        )

        if not department:

            departments = get_departments()

            self.state.current_question = "department"

            return {
                "type": "question",
                "field": "department",
                "message": (
                    "I couldn't confidently determine the department "
                    "from your request. Please select the appropriate "
                    "department below."
                ),
                "options": departments,
            }

        self.state.department = department


        # ----------------------------------------------
        # STEP 1: Request Type
        # ----------------------------------------------

        if not self.state.request_type:

            valid_request_types = REQUEST_TYPES.get(
                self.state.department,
                []
            )

            if not valid_request_types:

                return {
                    "type": "message",
                    "message": (
                        f"No request types are configured for "
                        f"{self.state.department}. "
                        "Please check the department configuration."
                    ),
                }

            self.state.current_question = "request_type"

            return {
                "type": "question",
                "field": "request_type",
                "message": (
                    f"I understand this is a "
                    f"{self.state.department} request.\n\n"
                    f"What type of request would you like to create?"
                ),
                "department": self.state.department,
                "options": valid_request_types,
            }

        # ----------------------------------------------
        # AI CATEGORY + SUBCATEGORY CLASSIFICATION
        # ----------------------------------------------

        if (
            not self.state.selected_category
            or not self.state.subcategory
        ):

            department_categories = CATEGORIES.get(
                self.state.department,
                {}
            )

            request_type_mapping = SUBCATEGORY_REQUEST_TYPES.get(
                self.state.department,
                {}
            )

            # Build a filtered catalog containing ONLY combinations
            # valid for the request type selected by the employee.
            filtered_categories = {}

            for category, subcategories in department_categories.items():

                valid_subcategories = []

                for subcategory in subcategories:

                    allowed_request_types = (
                        request_type_mapping
                        .get(category, {})
                        .get(subcategory, [])
                    )

                    if self.state.request_type in allowed_request_types:
                        valid_subcategories.append(subcategory)

                if valid_subcategories:
                    filtered_categories[category] = valid_subcategories

            # Run AI classification only when:
            # 1. We have a description
            # 2. We have valid mapped combinations
            if self.state.description and filtered_categories:

                classification = self.orchestrator.classify_category(
                    description=self.state.description,
                    department=self.state.department,
                    request_type=self.state.request_type,
                    allowed_categories=filtered_categories,
                )

                category = classification.get("category")
                subcategory = classification.get("subcategory")

                if category and subcategory:
                    self.state.selected_category = category
                    self.state.subcategory = subcategory
        
        # ----------------------------------------------
        # STEP 2: Location
        # ----------------------------------------------

        if not self.state.location:

            self.state.current_question = "location"

            return {
                "type": "question",
                "field": "location",
                "message": (
                    "Which location is this request related to?"
                ),
                "options": LOCATIONS,
            }

        # ----------------------------------------------
        # STEP 3: Category
        # ----------------------------------------------

        department = self.state.department

        department_categories = CATEGORIES.get(
            department,
            {}
        )

        if not department_categories:

            return {
                "type": "message",
                "message": (
                    f"I couldn't find categories for the "
                    f"{department} department."
                ),
            }

        if not self.state.selected_category:

            request_type_mapping = SUBCATEGORY_REQUEST_TYPES.get(
                department,
                {}
            )

            filtered_categories = {}

            for category, subcategories in department_categories.items():

                valid_subcategories = []

                for subcategory in subcategories:

                    allowed_request_types = (
                        request_type_mapping
                        .get(category, {})
                        .get(subcategory, [])
                    )

                    if self.state.request_type in allowed_request_types:
                        valid_subcategories.append(subcategory)

                if valid_subcategories:
                    filtered_categories[category] = valid_subcategories

            if not filtered_categories:
                return {
                    "type": "message",
                    "message": (
                        f"No categories are configured for "
                        f"{self.state.request_type} under "
                        f"{department}."
                    ),
                }

            self.state.current_question = "category"

            return {
                "type": "question",
                "field": "category",
                "message": (
                    "Which category is this request related to?"
                ),
                "options": list(filtered_categories.keys()),
            }

        # ----------------------------------------------
        # STEP 4: Subcategory
        # ----------------------------------------------

        selected_category = self.state.selected_category

        category_subcategories = CATEGORIES.get(
            department,
            {}
        ).get(
            selected_category,
            []
        )

        # Only keep subcategories valid for the selected request type
        request_type_mapping = SUBCATEGORY_REQUEST_TYPES.get(
            department,
            {}
        )

        valid_subcategories = []

        for subcategory in category_subcategories:

            allowed_request_types = (
                request_type_mapping
                .get(selected_category, {})
                .get(subcategory, [])
            )

            if self.state.request_type in allowed_request_types:
                valid_subcategories.append(subcategory)


        if not self.state.subcategory:

            if not valid_subcategories:

                return {
                    "type": "message",
                    "message": (
                        f"No subcategories are configured for "
                        f"{selected_category} under "
                        f"{self.state.request_type}."
                    ),
                }

            self.state.current_question = "subcategory"

            return {
                "type": "question",
                "field": "subcategory",
                "message": (
                    f"Which subcategory under {selected_category} "
                    "is this request related to?"
                ),
                "options": valid_subcategories,
            }
        # ----------------------------------------------
        # STEP 5: Description
        # ----------------------------------------------

        missing = self.state.get_missing_fields()

        if "description" in missing:

            self.state.current_question = "description"

            return {
                "type": "question",
                "field": "description",
                "message": (
                    "Please describe the issue or requirement "
                    "in detail."
                ),
                "input_type": "text",
                "placeholder": (
                    "Type your issue or requirement here..."
                ),
            }

        # ----------------------------------------------
        # STEP 6: Priority
        # ----------------------------------------------

        valid_priorities = [
            "High",
            "Medium",
            "Low",
        ]

        if not self.state.priority:

            self.state.current_question = "priority"

            return {
                "type": "question",
                "field": "priority",
                "message": (
                    "What priority should this ticket have?"
                ),
                "options": valid_priorities,
            }

        # ----------------------------------------------
        # STEP 7: Service Request custom fields
        # ----------------------------------------------

        service_request_custom_fields_required = (
            self.state.request_type == "Service Request"
            and self.state.department != "Strategy"
        )

        # Target Date
        if service_request_custom_fields_required:

            if not getattr(self.state, "target_date", None):

                self.state.current_question = "target_date"

                return {
                    "type": "question",
                    "field": "target_date",
                    "message": "When do you need this service or requirement completed?",
                    "input_type": "date",
                    "placeholder": "Select target date",
                }

        # Business Justification
        if service_request_custom_fields_required:

            if not getattr(self.state, "business_justification", None):

                self.state.current_question = "business_justification"

                return {
                    "type": "question",
                    "field": "business_justification",
                    "message": (
                        "Why is this service or requirement needed? "
                        "Please provide the business justification."
                    ),
                    "input_type": "text",
                    "placeholder": "Enter the business justification...",
                }

        # ----------------------------------------------
        # HR Service Request: Urgency
        # ----------------------------------------------

        if (
            self.state.department == "HR Department"
            and self.state.request_type == "Service Request"
        ):

            if not getattr(self.state, "urgency", None):

                self.state.current_question = "urgency"

                return {
                    "type": "question",
                    "field": "urgency",
                    "message": "What is the urgency of this request?",
                    "options": [
                        "High - Work is completely blocked",
                        "Medium - Work is significantly hindered",
                        "Low - Work can continue with limitations",
                    ],
                }

        # ----------------------------------------------
        # IT Service Request / Incident Request: Contact Details
        # ----------------------------------------------

        if (
            self.state.department == "IT Department"
            and self.state.request_type in [
                "Service Request",
                "Incident Request",
            ]
        ):

            # Vishakha Email
            if not getattr(self.state, "email", None):

                self.state.current_question = "email"

                return {
                    "type": "question",
                    "field": "email",
                    "message": "Please enter your Vishakha email address.",
                    "input_type": "text",
                    "placeholder": "name@vishakha.com",
                }

            # Phone Number
            if not getattr(self.state, "phone", None):

                self.state.current_question = "phone"

                return {
                    "type": "question",
                    "field": "phone",
                    "message": "Please enter your contact number.",
                    "input_type": "text",
                    "placeholder": "Enter phone number",
                }

        # ----------------------------------------------
        # STEP 7: Impact (Incident Requests only)
        # ----------------------------------------------

        if (
            self.state.request_type == "Incident Request"
            and self.state.department != "IT Department"
            and not self.state.start_time
        ):
            valid_impacts = [
                "High",
                "Medium",
                "Low",
            ]

            if not getattr(self.state, "impact", None):

                self.state.current_question = "impact"

                return {
                    "type": "question",
                    "field": "impact",
                    "message": (
                        "What is the impact of this incident?"
                    ),
                    "options": [
                        "High - Service is completely unavailable",
                        "Medium - Service is significantly degraded",
                        "Low - Minor functionality is affected",
                    ],
                }

        # ----------------------------------------------
        # Incident Start Time
        # ----------------------------------------------

        if (
            self.state.request_type == "Incident Request"
            and self.state.department != "IT Department"
            and not self.state.start_time
        ):
            self.state.current_question = "start_time"

            return {
                "type": "question",
                "field": "start_time",
                "message": "When did this incident start?",
                "input_type": "datetime-local",
                "placeholder": "Select incident start date and time",
            }

        # ----------------------------------------------
        # STEP 8: Confirmation
        # ----------------------------------------------

        self.state.current_question = "confirmation"

        return {
            "type": "confirmation",
            "message": "Please confirm the ticket details.",
            "ticket": self.state.get_summary(),
            "options": [
                "Confirm & Create Ticket",
                "Change Details",
                "Cancel",

            ],
        }

    def normalize_department(self, department):
        if not department:
            return None

        aliases = {
            "IT": "IT Department",
            "HR": "HR Department",
        }

        department = department.strip()

        if department in aliases:
            department = aliases[department]

        valid_departments = get_departments()

        for valid_department in valid_departments:
            if department.lower() == valid_department.lower():
                return valid_department

        return None
    
    def handle_option(self, option):

        field = self.state.current_question

        if not field:
            return {
                "type": "message",
                "message": "There is no pending question.",
            }

        # ----------------------------------------------
        # Confirmation
        # ----------------------------------------------

        if field == "confirmation":

            if option == "Confirm & Create Ticket":
                return self.confirm_ticket()

            if option == "Change Details":

                self.state.current_question = "change_field"

                change_options = [
                    "Department",
                    "Request Type",
                    "Category",
                    "Subcategory",
                    "Description",
                    "Location",
                    "Priority",
                ]

                # Service Request specific fields
                if self.state.request_type == "Service Request":

                    if getattr(self.state, "target_date", None):
                        change_options.append("Target Date")

                    if getattr(self.state, "business_justification", None):
                        change_options.append("Business Justification")

                # IT specific fields
                if self.state.department == "IT Department":

                    if getattr(self.state, "email", None):
                        change_options.append("Vishakha Email")

                    if getattr(self.state, "phone", None):
                        change_options.append("Phone Number")

                # Incident specific fields
                if self.state.request_type == "Incident Request":

                    if getattr(self.state, "impact", None):
                        change_options.append("Impact")

                    if getattr(self.state, "start_time", None):
                        change_options.append("Incident Start Time")

                # HR Service Request specific field
                if (
                    self.state.department == "HR Department"
                    and self.state.request_type == "Service Request"
                    and getattr(self.state, "urgency", None)
                ):
                    change_options.append("Urgency")

                self.state.current_question = "change_field"

                return {
                    "type": "question",
                    "field": "change_field",
                    "message": "Which ticket detail would you like to change?",
                    "options": change_options,
                }

            if option == "Cancel":
                return self.cancel()

            return {
                "type": "question",
                "field": "confirmation",
                "message": "Please select one of the available options.",
                "options": [
                    "Confirm & Create Ticket",
                    "Change Details",
                    "Cancel",
                ],
            }

        # ----------------------------------------------
        # Change Ticket Detail
        # ----------------------------------------------

        if field == "change_field":

            field_mapping = {
                "Department": "department",
                "Request Type": "request_type",
                "Category": "category",
                "Subcategory": "subcategory",
                "Description": "description",
                "Location": "location",
                "Priority": "priority",
                "Target Date": "target_date",
                "Business Justification": "business_justification",
                "Vishakha Email": "email",
                "Phone Number": "phone",
                "Impact": "impact",
                "Incident Start Time": "start_time",
                "Urgency": "urgency",
            }



            selected_field = field_mapping.get(option)

            if not selected_field:
                return {
                    "type": "question",
                    "field": "change_field",
                    "message": "Please select the ticket detail you want to change.",
                    "options": list(field_mapping.keys()),
                }

            # Clear the selected value so the normal workflow
            # can ask for it again.
            if selected_field == "department":
                self.state.department = None
                self.state.request_type = None

                # Department/request-type dependent fields
                self.state.selected_category = None
                self.state.category = None
                self.state.subcategory = None

                # Service Request specific fields
                self.state.target_date = None
                self.state.business_justification = None
                self.state.urgency = None

                # Incident specific fields
                self.state.impact = None
                self.state.start_time = None

                # IT specific fields
                self.state.email = None
                self.state.phone = None

                self.state.current_question = "department"

                return {
                    "type": "question",
                    "field": "department",
                    "message": "Please select the new department.",
                    "options": get_departments(),
                }

            elif selected_field == "request_type":
                self.state.request_type = None

                # Category depends on request type
                self.state.selected_category = None
                self.state.category = None
                self.state.subcategory = None

                # Clear Service Request specific fields
                self.state.target_date = None
                self.state.business_justification = None
                self.state.urgency = None

                # Clear Incident specific fields
                self.state.impact = None
                self.state.start_time = None

                # IT fields may differ between IT Incident and IT Service Request
                self.state.email = None
                self.state.phone = None

                self.state.current_question = "request_type"

                return {
                    "type": "question",
                    "field": "request_type",
                    "message": "Please select the new request type.",
                    "options": REQUEST_TYPES.get(
                        self.state.department,
                        []
                    ),
                }

            elif selected_field == "category":
                self.state.selected_category = None
                self.state.category = None
                self.state.subcategory = None

                department_categories = CATEGORIES.get(
                    self.state.department,
                    {}
                )

                request_type_mapping = SUBCATEGORY_REQUEST_TYPES.get(
                    self.state.department,
                    {}
                )

                # Only show categories that contain at least one
                # subcategory valid for the selected request type.
                filtered_categories = {}

                for category, subcategories in department_categories.items():

                    valid_subcategories = []

                    for subcategory in subcategories:

                        allowed_request_types = (
                            request_type_mapping
                            .get(category, {})
                            .get(subcategory, [])
                        )

                        if self.state.request_type in allowed_request_types:
                            valid_subcategories.append(subcategory)

                    if valid_subcategories:
                        filtered_categories[category] = valid_subcategories

                self.state.current_question = "category"

                return {
                    "type": "question",
                    "field": "category",
                    "message": "Please select the new category.",
                    "options": list(filtered_categories.keys()),
                }

            elif selected_field == "email":
                self.state.email = None
                self.state.current_question = "email"

                return {
                    "type": "question",
                    "field": "email",
                    "message": "Please enter the new Vishakha Email.",
                    "input_type": "text",
                    "placeholder": "Enter Vishakha Email...",
                }

            elif selected_field == "phone":
                self.state.phone = None
                self.state.current_question = "phone"

                return {
                    "type": "question",
                    "field": "phone",
                    "message": "Please enter the new Phone Number.",
                    "input_type": "text",
                    "placeholder": "Enter Phone Number...",
                }

            elif selected_field == "impact":
                self.state.impact = None
                self.state.current_question = "impact"

                return {
                    "type": "question",
                    "field": "impact",
                    "message": "Please select the new impact.",
                    "options": [
                        "High - Service is completely unavailable",
                        "Medium - Service is significantly degraded",
                        "Low - Minor functionality is affected",
                    ],
                }

            elif selected_field == "start_time":
                self.state.start_time = None
                self.state.current_question = "start_time"

                return {
                    "type": "question",
                    "field": "start_time",
                    "message": "Please select the new incident start date and time.",
                    "input_type": "datetime-local",
                    "placeholder": "Select incident start date and time",
                }

            elif selected_field == "urgency":
                self.state.urgency = None
                self.state.current_question = "urgency"

                return {
                    "type": "question",
                    "field": "urgency",
                    "message": "Please select the new urgency.",
                    "options": [
                        "High - Work is completely blocked",
                        "Medium - Work is significantly hindered",
                        "Low - Work can continue with limitations",
                    ],
                }

            elif selected_field == "subcategory":
                self.state.subcategory = None

                category_subcategories = CATEGORIES.get(
                    self.state.department,
                    {}
                ).get(
                    self.state.selected_category,
                    []
                )

                request_type_mapping = SUBCATEGORY_REQUEST_TYPES.get(
                    self.state.department,
                    {}
                )

                valid_subcategories = []

                for subcategory in category_subcategories:

                    allowed_request_types = (
                        request_type_mapping
                        .get(self.state.selected_category, {})
                        .get(subcategory, [])
                    )

                    if self.state.request_type in allowed_request_types:
                        valid_subcategories.append(subcategory)

                self.state.current_question = "subcategory"

                return {
                    "type": "question",
                    "field": "subcategory",
                    "message": (
                        f"Please select the new subcategory under "
                        f"{self.state.selected_category}."
                    ),
                    "options": valid_subcategories,
                }

            elif selected_field == "description":
                self.state.description = None

            elif selected_field == "location":
                self.state.location = None

            elif selected_field == "priority":
                self.state.priority = None

            elif selected_field == "target_date":
                self.state.target_date = None

            elif selected_field == "business_justification":
                self.state.business_justification = None

            self.state.current_question = None

            return self.handle_create_ticket()

        # ----------------------------------------------
        # Department
        # ----------------------------------------------

        if field == "department":

            valid_departments = get_departments()

            if option not in valid_departments:

                return {
                    "type": "question",
                    "field": "department",
                    "message": "Please select a valid department.",
                    "options": valid_departments,
                }

            self.state.department = option

            # Clear dependent fields
            self.state.request_type = None
            self.state.selected_category = None
            self.state.category = None
            self.state.subcategory = None

            self.state.current_question = None

            return self.handle_create_ticket()        

        # ----------------------------------------------
        # Request Type
        # ----------------------------------------------

        if field == "request_type":

            # User wants to override the department inferred by AI
            if option == "Change Department":

                self.state.department = None
                self.state.request_type = None

                self.state.selected_category = None
                self.state.category = None
                self.state.subcategory = None

                self.state.current_question = "department"

                return {
                    "type": "question",
                    "field": "department",
                    "message": "Please select the correct department.",
                    "options": get_departments(),
                }

            valid_request_types = REQUEST_TYPES.get(
                self.state.department,
                []
            )

            if option not in valid_request_types:

                return {
                    "type": "question",
                    "field": "request_type",
                    "message": (
                        "Please select a valid request type."
                    ),
                    "options": valid_request_types,
                }

            recommended_request_type = (
                self.orchestrator.classify_request_type(
                    description=self.state.description,
                    department=self.state.department,
                    allowed_request_types=valid_request_types,
                )
            )

            print(
                "\nREQUEST TYPE CHECK:",
                {
                    "selected": option,
                    "recommended": recommended_request_type,
                }
            )

            # Store the employee's selected request type first.
            self.state.request_type = option

            # If AI believes another allowed request type is a better
            # match, warn the employee instead of silently changing it.
            if (
                recommended_request_type
                and recommended_request_type != option
            ):
                self.state.current_question = (
                    "request_type_mismatch"
                )

                return {
                    "type": "question",
                    "field": "request_type_mismatch",
                    "message": (
                        f"Your description appears to be a "
                        f"{recommended_request_type}, but you selected "
                        f"{option}.\n\n"
                        f"Would you like to switch to "
                        f"{recommended_request_type} or continue with "
                        f"{option}?"
                    ),
                    "options": [
                        f"Switch to {recommended_request_type}",
                        f"Continue with {option}",
                    ],
                }

            self.state.current_question = None

            return self.handle_create_ticket()

        # ----------------------------------------------
        # Request Type Mismatch Confirmation
        # ----------------------------------------------

        if field == "request_type_mismatch":

            current_request_type = self.state.request_type

            # ------------------------------------------
            # Switch to AI-recommended request type
            # ------------------------------------------

            if option.startswith("Switch to "):

                new_request_type = option.replace(
                    "Switch to ",
                    "",
                    1,
                ).strip()

                valid_request_types = REQUEST_TYPES.get(
                    self.state.department,
                    [],
                )

                # Security check:
                # Never accept a request type outside the
                # department's configured request types.
                if new_request_type not in valid_request_types:

                    return {
                        "type": "message",
                        "message": (
                            "The selected request type is not valid "
                            "for this department."
                        ),
                    }

                self.state.request_type = new_request_type

                # Request type changed, so previously determined
                # category/subcategory can no longer be trusted.
                self.state.selected_category = None
                self.state.category = None
                self.state.subcategory = None

                self.state.current_question = None

                return self.handle_create_ticket()

            # ------------------------------------------
            # Keep employee's original selection
            # ------------------------------------------

            if option == f"Continue with {current_request_type}":

                self.state.current_question = None

                return self.handle_create_ticket()

            # ------------------------------------------
            # Invalid response
            # ------------------------------------------

            return {
                "type": "question",
                "field": "request_type_mismatch",
                "message": (
                    "Please choose whether you want to switch "
                    "the request type or continue with your "
                    "original selection."
                ),
                "options": [
                    f"Continue with {current_request_type}",
                ],
            }

        # ----------------------------------------------
        # Target Date
        # ----------------------------------------------

        if field == "target_date":

            selected_date = option.strip()

            try:
                parsed_date = datetime.strptime(
                    selected_date,
                    "%Y-%m-%d"
                ).date()

            except ValueError:
                self.state.current_question = "target_date"

                return {
                    "type": "question",
                    "field": "target_date",
                    "message": "Invalid date. Please select a valid date.",
                    "input_type": "date",
                    "placeholder": "Select target date",
                }

            today = timezone.localdate()

            if parsed_date < today:
                self.state.current_question = "target_date"

                return {
                    "type": "question",
                    "field": "target_date",
                    "message": "Past dates are not allowed. Please select today or a future date.",
                    "input_type": "date",
                    "placeholder": "Select target date",
                }

            self.state.target_date = parsed_date.isoformat()
            self.state.current_question = None

            return self.handle_create_ticket()
        # ----------------------------------------------
        # Business Justification
        # ----------------------------------------------

        if field == "business_justification":

            if not option.strip():

                return {
                    "type": "question",
                    "field": "business_justification",
                    "message": "Please enter the business justification.",
                    "input_type": "text",
                    "placeholder": "Enter the business justification...",
                }

            self.state.business_justification = option.strip()
            self.state.current_question = None

            return self.handle_create_ticket()

        # ----------------------------------------------
        # IT Service Request: Email
        # ----------------------------------------------

        if field == "email":

            email = option.strip()

            if not email:
                return {
                    "type": "question",
                    "field": "email",
                    "message": "Please enter your Vishakha email address.",
                    "input_type": "text",
                    "placeholder": "name@vishakha.com",
                }

            self.state.email = email
            self.state.current_question = None

            return self.handle_create_ticket()

        # ----------------------------------------------
        # IT Service Request: Phone Number
        # ----------------------------------------------

        if field == "phone":

            phone = option.strip()

            if not phone:
                return {
                    "type": "question",
                    "field": "phone",
                    "message": "Please enter your contact number.",
                    "input_type": "text",
                    "placeholder": "Enter phone number",
                }

            self.state.phone = phone
            self.state.current_question = None

            return self.handle_create_ticket()

        # ----------------------------------------------
        # HR Service Request: Urgency
        # ----------------------------------------------

        if field == "urgency":

            valid_urgencies = {
                "High - Work is completely blocked":
                    "High - Work is completely blocked",

                "Medium - Work is significantly hindered":
                    "Medium\t- Work is significantly hindered",

                "Low - Work can continue with limitations":
                    "Low - Work can continue with limitations",
            }

            if option not in valid_urgencies:

                return {
                    "type": "question",
                    "field": "urgency",
                    "message": "Please select a valid urgency.",
                    "options": list(valid_urgencies.keys()),
                }

            self.state.urgency = valid_urgencies[option]
            self.state.current_question = None

            return self.handle_create_ticket()

        # ----------------------------------------------
        # Category
        # ----------------------------------------------

        if field == "category":

            department_categories = CATEGORIES.get(
                self.state.department,
                {}
            )

            if option not in department_categories:

                return {
                    "type": "question",
                    "field": "category",
                    "message": "Please select a valid category.",
                    "options": list(department_categories.keys()),
                }

            self.state.selected_category = option

            # Clear any old subcategory
            self.state.subcategory = None

            # Clear the old generic category value
            self.state.category = None

            self.state.current_question = None

            return self.handle_create_ticket()

        # ----------------------------------------------
        # Subcategory
        # ----------------------------------------------

        if field == "subcategory":

            department = self.state.department
            selected_category = self.state.selected_category

            valid_subcategories = CATEGORIES.get(
                department, {}
            ).get(
                selected_category, []
            )

            if option not in valid_subcategories:

                return {
                    "type": "question",
                    "field": "subcategory",
                    "message": "Please select a valid subcategory.",
                    "options": valid_subcategories,
                }

            self.state.subcategory = option
            self.state.current_question = None

            return self.handle_create_ticket()

        # ----------------------------------------------
        # Description
        # ----------------------------------------------

        if field == "description":

            description = option.strip()

            if not description or description.lower() == "other":

                return {
                    "type": "question",
                    "field": "description",
                    "message": (
                        "Please enter a description of the "
                        "issue or requirement."
                    ),
                    "input_type": "text",
                    "placeholder": (
                        "Type your issue or requirement here..."
                    ),
                }

            self.state.description = description
            self.state.current_question = None

            return self.handle_create_ticket()

        # ----------------------------------------------
        # Location
        # ----------------------------------------------

        if field == "location":

            if option not in LOCATIONS:

                return {
                    "type": "question",
                    "field": "location",
                    "message": "Please select a valid location.",
                    "options": LOCATIONS,
                }

            self.state.location = option
            self.state.current_question = None

            return self.handle_create_ticket()


        # ----------------------------------------------
        # Priority
        # ----------------------------------------------

        if field == "priority":

            valid_priorities = [
                "High",
                "Medium",
                "Low",
            ]

            if option not in valid_priorities:

                return {
                    "type": "question",
                    "field": "priority",
                    "message": (
                        "Please select a valid priority."
                    ),
                    "options": valid_priorities,
                }

            self.state.priority = option
            self.state.current_question = None

            return self.handle_create_ticket()

        # ----------------------------------------------
        # Impact
        # ----------------------------------------------

        if field == "impact":

            valid_impacts = {
                "High - Service is completely unavailable": "High",
                "Medium - Service is significantly degraded": "Medium",
                "Low - Minor functionality is affected": "Low",
            }

            if option not in valid_impacts:

                return {
                    "type": "question",
                    "field": "impact",
                    "message": (
                        "Please select a valid impact level."
                    ),
                    "options": list(valid_impacts.keys()),
                }

            self.state.impact = valid_impacts[option]
            self.state.current_question = None

            return self.handle_create_ticket()

        # ----------------------------------------------
        # Incident Start Time
        # ----------------------------------------------

        if field == "start_time":

            start_time = option.strip()

            if not start_time:

                return {
                    "type": "question",
                    "field": "start_time",
                    "message": "Please select when the incident started.",
                    "input_type": "datetime-local",
                    "placeholder": "Select incident start date and time",
                }

            try:
                parsed_datetime = datetime.fromisoformat(start_time)

            except ValueError:

                return {
                    "type": "question",
                    "field": "start_time",
                    "message": "Please select a valid incident start date and time.",
                    "input_type": "datetime-local",
                    "placeholder": "Select incident start date and time",
                }

            now = timezone.localtime()

            if timezone.is_naive(parsed_datetime):
                parsed_datetime = timezone.make_aware(
                    parsed_datetime,
                    timezone.get_current_timezone()
                )

            # Allow a small tolerance for "just now".
            # This avoids rejecting a time that is only slightly ahead
            # because of browser/server clock differences.
            future_tolerance = timedelta(minutes=2)

            if parsed_datetime > now + future_tolerance:

                return {
                    "type": "question",
                    "field": "start_time",
                    "message": "Incident start time cannot be in the future.",
                    "input_type": "datetime-local",
                    "placeholder": "Select incident start date and time",
                }

            self.state.start_time = parsed_datetime.isoformat()
            self.state.current_question = None

            return self.handle_create_ticket()


    def get_department_search_config(self, department):
        """
        Return ticket-search configuration for a department.

        Example:
        IT Department -> ticket type IDs [55, 56]
        """

        if not department:
            return None

        return DEPARTMENT_SEARCH_CONFIG.get(department)

    def search_department_tickets(
        self,
        department,
        search_scope="ALL_TICKETS",
        search_query=None,
        status_ids=None,
        category_id=None,
        subcategory_id=None,
        ticket_type_id=None,
        include_closed=True,
        size=20,
    ):
        """
        Search tickets for any configured department.

        Supports:
        1. Simple ticket-type filtering
        2. Ticket-type + group routing filtering

        Returns:
        {
            "content": [...],
            "totalElements": 0,
        }
        """

        config = self.get_department_search_config(department)

        if not config:
            return {
                "content": [],
                "totalElements": 0,
            }

        # ----------------------------------------------
        # Build department search routes
        # ----------------------------------------------
        routes = config.get("routes")

        if not routes:
            routes = [
                {
                    "ticket_type_id": ticket_type_id,
                    "group_ids": None,
                }
                for ticket_type_id in config.get(
                    "ticket_type_ids",
                    []
                )
            ]

        # If structured catalog search already determined
        # the exact request/ticket type, search only that type.
        if ticket_type_id is not None:

            routes = [
                route
                for route in routes
                if route.get("ticket_type_id")
                == ticket_type_id
            ]

        combined_tickets = []
        total = 0

        # ----------------------------------------------
        # Search each department route
        # ----------------------------------------------
        for route in routes:

            ticket_type_id = route.get("ticket_type_id")
            group_ids = route.get("group_ids")

            if search_scope == "MY_TICKETS":

                if search_query:
                    result = self.ticketing.search_my_tickets(
                        search_query=search_query,
                        requester_email=self.requester_email,
                        include_closed=include_closed,
                        status_ids=status_ids,
                        ticket_type_id=ticket_type_id,
                        group_ids=group_ids,
                        category_id=category_id,
                        subcategory_id=subcategory_id,
                        size=size,
                    )

                else:
                    result = self.ticketing.get_my_tickets(
                        requester_email=self.requester_email,
                        include_closed=include_closed,
                        status_ids=status_ids,
                        ticket_type_id=ticket_type_id,
                        group_ids=group_ids,
                        category_id=category_id,
                        subcategory_id=subcategory_id,
                        size=size,
                    )

            else:

                if search_query:
                    result = self.ticketing.get_all_tickets(
                        search_query=search_query,
                        include_closed=include_closed,
                        status_ids=status_ids,
                        ticket_type_id=ticket_type_id,
                        group_ids=group_ids,
                        category_id=category_id,
                        subcategory_id=subcategory_id,
                        size=size,
                    )

                else:
                    result = self.ticketing.get_all_tickets(
                        include_closed=include_closed,
                        status_ids=status_ids,
                        ticket_type_id=ticket_type_id,
                        group_ids=group_ids,
                        category_id=category_id,
                        subcategory_id=subcategory_id,
                        size=size,
                    )

            total += result.get("totalElements", 0)

            combined_tickets.extend(
                result.get("content", [])
            )

        # ----------------------------------------------
        # Merge newest tickets first
        # ----------------------------------------------
        combined_tickets.sort(
            key=lambda ticket: ticket.get("createdAt") or "",
            reverse=True,
        )

        combined_tickets = combined_tickets[:size]

        return {
            "content": combined_tickets,
            "totalElements": total,
        }

    def handle_search_tickets(self):
        try:
            search_query = self.state.search_query
            search_scope = self.state.search_scope
            original_search_query = search_query
            search_department = getattr(
                self.state,
                "search_department",
                None,
            )
            status_filter = getattr(
                self.state,
                "ticket_status_filter",
                None,
            )

            count_only = getattr(
                self.state,
                "ticket_count_only",
                False,
            )

            # --------------------------------------------------
            # STRUCTURED CATEGORY / SUBCATEGORY SEARCH
            # --------------------------------------------------
            structured_category_id = None
            structured_subcategory_id = None
            structured_category_name = None
            structured_subcategory_name = None
            structured_request_types = []
            structured_ticket_type_id = None
            structured_ticket_type_ids = []
            structured_routes = []

            catalog_match = None

            if search_department and search_query:
                print(
                    "SEARCH QUERY BEFORE CATALOG:",
                    repr(search_query),
                )


                # STEP 1: Fast deterministic catalog matching
                catalog_match = find_catalog_item(
                    search_department,
                    search_query,
                )

                # STEP 2: AI semantic fallback
                # Run only when exact, partial and alias matching fail.
                if not catalog_match:

                    allowed_categories = CATEGORIES.get(
                        search_department,
                        {},
                    )

                    if allowed_categories:
                        try:
                            classification = (
                                self.orchestrator.classify_category(
                                    description=search_query,
                                    department=search_department,
                                    request_type=None,
                                    allowed_categories=allowed_categories,
                                    search_mode=True,
                                )
                            )

                            category = classification.get("category")
                            subcategory = classification.get("subcategory")

                            # Validate both values against the real catalog.
                            if (
                                category in allowed_categories
                                and subcategory
                                in allowed_categories.get(category, [])
                            ):
                                request_types = (
                                    SUBCATEGORY_REQUEST_TYPES
                                    .get(search_department, {})
                                    .get(category, {})
                                    .get(subcategory, [])
                                )

                                if request_types:
                                    catalog_match = {
                                        "category": category,
                                        "subcategory": subcategory,
                                        "request_types": list(request_types),
                                    }

                                    print(
                                        "AI SEMANTIC CATALOG MATCH:",
                                        catalog_match,
                                    )

                        except (ValueError, TypeError) as exc:
                            print(
                                "AI SEMANTIC MATCH FAILED:",
                                str(exc),
                            )

                print(
                    "CATALOG MATCH:",
                    catalog_match,
                )


                if catalog_match:

                    structured_category_name = catalog_match[
                        "category"
                    ]

                    structured_subcategory_name = catalog_match[
                        "subcategory"
                    ]

                    structured_request_types = catalog_match[
                        "request_types"
                    ]

                    search_query = None

            # --------------------------------------------------
            # RESOLVE STRUCTURED SEARCH TO LIVE PORTAL IDs
            # --------------------------------------------------

            if catalog_match:

                # Only resolve automatically when the catalog
                # points to exactly one request type.
                # Convert every catalog request type into its
                # corresponding Service Excellence ticket type ID.
                request_type_to_ticket_id = {
                    "Incident Request": {
                        "Admin": 9,
                        "Safety": 12,
                        "Security": 8,
                        "HR Department": 53,
                        "IT Department": 56,
                    },
                    "Service Request": {
                        "Admin": 11,
                        "Safety": 16,
                        "Branding": 6,
                        "HR Department": 52,
                        "Finance": 51,
                        "Insurance": 54,
                        "Compliance & Risk": 50,
                        "Strategy": 60,
                        "IT Department": 55,
                    },
                    "Change Management": {
                        "Branding": 14,
                        "Projects": 59,
                    },
                    "Request For Information": {
                        "Branding": 7,
                    },
                    "Customer Complaint": {
                        "Quality management": 61,
                    },
                }

                for request_type in structured_request_types:

                    ticket_type_id = (
                        request_type_to_ticket_id
                        .get(request_type, {})
                        .get(search_department)
                    )

                    if ticket_type_id is not None:
                        structured_ticket_type_ids.append(
                            ticket_type_id
                        )

                print(
                    "STRUCTURED TICKET TYPE IDS:",
                    structured_ticket_type_ids,
                )

                # Resolve the structured category/subcategory
                # independently for every applicable ticket type.
                if len(structured_ticket_type_ids) > 1:

                    for request_type, ticket_type_id in zip(
                        structured_request_types,
                        structured_ticket_type_ids,
                    ):

                        try:
                            resolved = (
                                self.ticketing
                                .resolve_category_subcategory(
                                    ticket_type_id=ticket_type_id,
                                    category_name=structured_category_name,
                                    subcategory_name=structured_subcategory_name,
                                )
                            )

                            structured_routes.append(
                                {
                                    "request_type": request_type,
                                    "ticket_type_id": ticket_type_id,
                                    "category_id": resolved["category_id"],
                                    "subcategory_id": resolved["subcategory_id"],
                                }
                            )

                        except Exception as exc:
                            print(
                                "STRUCTURED ROUTE RESOLUTION FAILED:",
                                ticket_type_id,
                                exc,
                            )

                    print(
                        "STRUCTURED ROUTES:",
                        structured_routes,
                    )

                if len(structured_request_types) == 1:

                    structured_request_type = (
                        structured_request_types[0]
                    )


                    structured_ticket_type_id = (
                        request_type_to_ticket_id
                        .get(
                            structured_request_type,
                            {},
                        )
                        .get(search_department)
                    )

                    if structured_ticket_type_id:

                        resolved = (
                            self.ticketing
                            .resolve_category_subcategory(
                                ticket_type_id=(
                                    structured_ticket_type_id
                                ),
                                category_name=(
                                    structured_category_name
                                ),
                                subcategory_name=(
                                    structured_subcategory_name
                                ),
                            )
                        )

                        structured_category_id = resolved[
                            "category_id"
                        ]

                        structured_subcategory_id = resolved[
                            "subcategory_id"
                        ]

                        print(
                            "STRUCTURED CATEGORY:",
                            structured_category_name,
                            structured_category_id,
                        )

                        print(
                            "STRUCTURED SUBCATEGORY:",
                            structured_subcategory_name,
                            structured_subcategory_id,
                        )

                        print(
                            "STRUCTURED REQUEST TYPE:",
                            structured_request_type,
                            structured_ticket_type_id,
                        )
                    
            def ticket_word(total):
                return "ticket" if total == 1 else "tickets"


            # --------------------------------------------------
            # CONSISTENT TICKET LISTING (BEFORE OLD LIST BRANCHES)
            # --------------------------------------------------
            # Personal department queries must stay requester-scoped.
            # Never discard a matched catalog's category filters.
            if search_scope == "MY_TICKETS" and catalog_match:
                # Enforce authenticated-requester restriction at API level.
                if not self.requester_email:
                    return {
                        "type": "error",
                        "message": "Your employee identity is unavailable for personal ticket search.",
                        "tickets": [],
                    }

                status_ids = (
                    TICKET_STATUS_IDS.get(status_filter)
                    if status_filter != "OPEN" else None
                )
                include_closed = status_filter != "OPEN"

                # Category-only: no keyword restriction. For specific
                # subcategories, use both category IDs and the item keyword.
                keyword = None
                if structured_subcategory_name and original_search_query:
                    candidate = str(original_search_query).strip()
                    if candidate.casefold() != structured_subcategory_name.casefold():
                        keyword = candidate

                routes = list(structured_routes)
                if not routes and structured_ticket_type_id is not None:
                    routes = [{
                        "ticket_type_id": structured_ticket_type_id,
                        "category_id": structured_category_id,
                        "subcategory_id": structured_subcategory_id,
                    }]

                # Fail closed: never substitute an unfiltered personal search
                # for a structured search whose catalog IDs failed to resolve.
                if (
                    not routes
                    or any(route.get("category_id") is None for route in routes)
                    or (structured_subcategory_name and any(
                        route.get("subcategory_id") is None for route in routes
                    ))
                ):
                    return {
                        "type": "error",
                        "message": "I couldn't resolve the required catalog filters for your tickets.",
                        "tickets": [],
                    }

                total = 0
                tickets = []
                breakdown = []
                for route in routes:
                    result = self.search_department_tickets(
                        department=search_department,
                        search_scope="MY_TICKETS",
                        search_query=keyword,
                        status_ids=status_ids,
                        include_closed=include_closed,
                        category_id=route["category_id"],
                        subcategory_id=route.get("subcategory_id"),
                        ticket_type_id=route["ticket_type_id"],
                        size=1 if count_only else 20,
                    )
                    route_total = result.get("totalElements", 0)
                    total += route_total
                    breakdown.append({
                        "label": TICKET_TYPE_NAMES.get(route["ticket_type_id"], "Request"),
                        "count": route_total,
                    })
                    if not count_only:
                        tickets.extend(result.get("content", []))

                tickets.sort(key=lambda t: t.get("createdAt") or "", reverse=True)
                print("PERSONAL STRUCTURED SEARCH:", {
                    "department": search_department,
                    "category": structured_category_name,
                    "subcategory": structured_subcategory_name,
                    "keyword": keyword,
                    "total": total,
                })
                return {
                    "type": "ticket_search_summary" if count_only else "ticket_list",
                    "message": f"I found {total} matching {ticket_word(total)} in your {search_department} tickets.",
                    "department": search_department,
                    "category": structured_category_name,
                    "subcategory": structured_subcategory_name,
                    "keyword": keyword,
                    "status": status_filter,
                    "total": total,
                    "breakdown": breakdown,
                    "tickets": [] if count_only else tickets[:20],
                }

            if search_scope == "MY_TICKETS" and search_department:
                config = self.get_department_search_config(search_department)
                if not config:
                    return {"type": "message", "message": "Department search is not configured.", "tickets": []}
                status_ids = (TICKET_STATUS_IDS.get(status_filter)
                              if status_filter != "OPEN" else None)
                include_closed = status_filter != "OPEN"
                total = 0
                tickets = []
                for tid in config.get("ticket_type_ids", []):
                    args = dict(
                        requester_email=self.requester_email,
                        ticket_type_id=tid,
                        status_ids=status_ids,
                        include_closed=include_closed,
                        size=1 if count_only else 20,
                    )
                    if search_query:
                        r = self.ticketing.search_my_tickets(search_query=search_query, **args)
                    else:
                        r = self.ticketing.get_my_tickets(**args)
                    total += r.get("totalElements", 0)
                    tickets.extend(r.get("content", []))
                tickets.sort(key=lambda t: t.get("createdAt") or "", reverse=True)
                return {
                    "type": "ticket_search_summary" if count_only else "ticket_list",
                    "message": f"I found {total} of your {search_department} {ticket_word(total)}.",
                    "total": total,
                    "tickets": [] if count_only else tickets[:20],
                }

            if not count_only and search_scope == "MY_TICKETS" and not search_department and not search_query:
                result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email,
                    include_closed=(status_filter != "OPEN"),
                    status_ids=(TICKET_STATUS_IDS.get(status_filter)
                                if status_filter != "OPEN" else None),
                    size=20,
                )
                return {
                    "type": "ticket_list",
                    "message": f"I found {result.get('totalElements', 0)} of your tickets.",
                    "total": result.get("totalElements", 0),
                    "tickets": result.get("content", []),
                }

            if not count_only and search_scope == "ALL_TICKETS" and search_department:
                status_ids = (TICKET_STATUS_IDS.get(status_filter)
                              if status_filter != "OPEN" else None)
                include_closed = (status_filter != "OPEN")
                keyword = original_search_query if original_search_query else None
                # For a category-only catalog match use the category
                # instead of searching its literal name in ticket text.
                if catalog_match and not structured_subcategory_name:
                    keyword = None
                elif catalog_match and keyword and structured_subcategory_name:
                    if keyword.casefold() == structured_subcategory_name.casefold():
                        keyword = None

                routes = []
                if catalog_match:
                    if structured_routes:
                        routes = structured_routes
                    elif structured_ticket_type_id is not None:
                        routes = [{
                            "ticket_type_id": structured_ticket_type_id,
                            "category_id": structured_category_id,
                            "subcategory_id": structured_subcategory_id,
                        }]
                    if not routes or any(r.get("category_id") is None for r in routes):
                        return {"type": "error", "message": "Catalog filter resolution failed.", "tickets": []}
                else:
                    config = self.get_department_search_config(search_department)
                    if not config:
                        return {"type": "message", "message": "Department search is not configured.", "tickets": []}
                    routes = [{"ticket_type_id": tid, "category_id": None, "subcategory_id": None}
                              for tid in config.get("ticket_type_ids", [])]

                results = []
                total = 0
                for route in routes:
                    r = self.search_department_tickets(
                        department=search_department,
                        search_scope="ALL_TICKETS",
                        search_query=keyword,
                        status_ids=status_ids,
                        include_closed=include_closed,
                        category_id=route["category_id"],
                        subcategory_id=route["subcategory_id"],
                        ticket_type_id=route["ticket_type_id"],
                        size=20,
                    )
                    total += r.get("totalElements", 0)
                    results.extend(r.get("content", []))
                results.sort(key=lambda t: t.get("createdAt") or "", reverse=True)
                return {
                    "type": "ticket_list",
                    "message": f"I found {total} matching {ticket_word(total)}.",
                    "total": total,
                    "tickets": results[:20],
                }

            # --------------------------------------------------
            # HYBRID SEARCH: STRUCTURED CATALOG + KEYWORD
            # Count-only searches across all accessible tickets.
            # --------------------------------------------------

            if (
                count_only
                and search_scope == "ALL_TICKETS"
                and search_department
                and catalog_match
                and structured_subcategory_name
                and original_search_query
            ):
                keyword = str(original_search_query).strip()

                # If the employee supplied the exact subcategory name,
                # retain existing category/subcategory-wide behavior.
                if keyword.casefold() != structured_subcategory_name.casefold():

                    status_ids = None
                    include_closed = True

                    if status_filter == "OPEN":
                        include_closed = False
                    elif status_filter in TICKET_STATUS_IDS:
                        status_ids = TICKET_STATUS_IDS[status_filter]

                    # Build separate routes because the same catalog
                    # names can have different IDs for each ticket type.
                    if structured_routes:
                        routes = structured_routes
                    elif structured_ticket_type_id is not None:
                        routes = [{
                            "request_type": structured_request_types[0],
                            "ticket_type_id": structured_ticket_type_id,
                            "category_id": structured_category_id,
                            "subcategory_id": structured_subcategory_id,
                        }]
                    else:
                        routes = []

                    # Do not widen a structured search when portal
                    # ID resolution has failed.
                    if not routes or any(
                        route.get("category_id") is None
                        or route.get("subcategory_id") is None
                        for route in routes
                    ):
                        return {
                            "type": "error",
                            "message": (
                                "I couldn't resolve the catalog filters "
                                "for this ticket search."
                            ),
                        }

                    total = 0
                    breakdown = []

                    for route in routes:
                        result = self.search_department_tickets(
                            department=search_department,
                            search_scope="ALL_TICKETS",
                            search_query=keyword,
                            status_ids=status_ids,
                            category_id=route["category_id"],
                            subcategory_id=route["subcategory_id"],
                            ticket_type_id=route["ticket_type_id"],
                            include_closed=include_closed,
                            size=1,
                        )

                        route_total = result.get("totalElements", 0)
                        total += route_total

                        breakdown.append({
                            "label": route["request_type"],
                            "count": route_total,
                        })

                    print("HYBRID SEARCH KEYWORD:", keyword)
                    print("HYBRID SEARCH TOTAL:", total)
                    print("HYBRID SEARCH BREAKDOWN:", breakdown)

                    return {
                        "type": "ticket_search_summary",
                        "message": (
                            f"I found {total} matching "
                            f"{ticket_word(total)} for '{keyword}' "
                            f"under {structured_category_name} / "
                            f"{structured_subcategory_name}."
                        ),
                        "department": search_department,
                        "category": structured_category_name,
                        "subcategory": structured_subcategory_name,
                        "keyword": keyword,
                        "status": (
                            "Open"
                            if status_filter == "OPEN"
                            else status_filter
                        ),
                        "total": total,
                        "breakdown": breakdown,
                        "tickets": [],
                    }


            # --------------------------------------------------
            # COUNT ONLY: DEPARTMENT TICKETS
            # --------------------------------------------------
            if (
                count_only
                and search_scope == "ALL_TICKETS"
                and search_department
                and not status_filter
                and not search_query
                ):

                department_config = self.get_department_search_config(
                    search_department
                )

                if not department_config:
                    return {
                        "type": "message",
                        "message": (
                            f"Ticket search for {search_department} "
                            f"is not configured yet."
                        ),
                        "total": 0,
                        "tickets": [],
                    }
                print(
                    "STRUCTURED CATEGORY ID:",
                    structured_category_id
                )

                # Multi-request-type structured search.
                # Each ticket type can have different category/subcategory IDs.
                structured_route_totals = []
                if structured_routes:

                    total = 0
                    
                    

                    for route in structured_routes:

                        result = self.search_department_tickets(
                            department=search_department,
                            search_scope="ALL_TICKETS",
                            category_id=route["category_id"],
                            subcategory_id=route["subcategory_id"],
                            ticket_type_id=route["ticket_type_id"],
                            include_closed=True,
                            size=1,
                        )

                        route_total = result.get(
                            "totalElements",
                            0,
                        )

                        print(
                            "STRUCTURED ROUTE TOTAL:",
                            route["ticket_type_id"],
                            route_total,
                        )

                        total += route_total

                        structured_route_totals.append(
                            {
                                "request_type": route["request_type"],
                                "ticket_type_id": route["ticket_type_id"],
                                "total": route_total,
                            }
                        )

                        print(
                            "STRUCTURED ROUTE TOTALS:",
                            structured_route_totals,
                        )

                else:

                    result = self.search_department_tickets(
                        department=search_department,
                        search_scope="ALL_TICKETS",
                        category_id=structured_category_id,
                        subcategory_id=structured_subcategory_id,
                        ticket_type_id=structured_ticket_type_id,
                        include_closed=True,
                        size=1,
                    )

                    total = result.get(
                        "totalElements",
                        0,
                    )


                return {
                    "type": "ticket_search_summary",

                    "message": (
                        "I found no matching tickets."
                        if total == 0
                        else (
                            f"I found {total} matching "
                            f"{ticket_word(total)}."
                        )
                    ),

                    "department": search_department,

                    "category": structured_category_name,

                    "subcategory": structured_subcategory_name,

                    "status": None,

                    "total": total,

                    "breakdown": [
                        {
                            "label": item["request_type"],
                            "count": item["total"],
                        }
                        for item in structured_route_totals
                    ],

                    "tickets": [],
                }

            # --------------------------------------------------
            # COUNT ONLY: OPEN DEPARTMENT TICKETS
            # --------------------------------------------------
            if (
                count_only
                and search_scope == "ALL_TICKETS"
                and search_department
                and status_filter == "OPEN"
                and not search_query
            ):
                department_config = self.get_department_search_config(
                    search_department
                )

                if not department_config:
                    return {
                        "type": "message",
                        "message": (
                            f"Ticket search for {search_department} "
                            f"is not configured yet."
                        ),
                        "total": 0,
                        "tickets": [],
                    }

                structured_route_totals = []

                # ----------------------------------------------
                # Multi-request-type structured search
                # Example:
                # IT Network / Internet Connectivity
                # -> Incident + Service Request
                # ----------------------------------------------
                if structured_routes:

                    total = 0

                    for route in structured_routes:

                        result = self.search_department_tickets(
                            department=search_department,
                            search_scope="ALL_TICKETS",
                            category_id=route["category_id"],
                            subcategory_id=route["subcategory_id"],
                            ticket_type_id=route["ticket_type_id"],

                            # OPEN in Darpan means all active /
                            # non-closed workflow states.
                            include_closed=False,

                            size=1,
                        )

                        route_total = result.get(
                            "totalElements",
                            0,
                        )

                        total += route_total

                        structured_route_totals.append(
                            {
                                "request_type": route["request_type"],
                                "total": route_total,
                            }
                        )

                # ----------------------------------------------
                # Single request type / department-only search
                # ----------------------------------------------
                else:

                    result = self.search_department_tickets(
                        department=search_department,
                        search_scope="ALL_TICKETS",
                        category_id=structured_category_id,
                        subcategory_id=structured_subcategory_id,
                        ticket_type_id=structured_ticket_type_id,

                        # Keep existing Darpan OPEN semantics.
                        include_closed=False,

                        size=1,
                    )

                    total = result.get(
                        "totalElements",
                        0,
                    )

                return {
                    "type": "ticket_search_summary",

                    "message": (
                        "I found no matching tickets."
                        if total == 0
                        else (
                            f"I found {total} matching "
                            f"{ticket_word(total)}."
                        )
                    ),

                    "department": search_department,

                    "category": structured_category_name,

                    "subcategory": structured_subcategory_name,

                    "status": "Open",

                    "total": total,

                    "breakdown": [
                        {
                            "label": item["request_type"],
                            "count": item["total"],
                        }
                        for item in structured_route_totals
                    ],

                    "tickets": [],
                }

            # --------------------------------------------------
            # COUNT ONLY: DEPARTMENT TICKETS BY EXACT STATUS
            # --------------------------------------------------
            if (
                count_only
                and search_scope == "ALL_TICKETS"
                and search_department
                and status_filter in TICKET_STATUS_IDS
                and not search_query
            ):
                status_ids = TICKET_STATUS_IDS[status_filter]

                structured_route_totals = []

                if structured_routes:

                    total = 0

                    for route in structured_routes:

                        result = self.search_department_tickets(
                            department=search_department,
                            search_scope="ALL_TICKETS",
                            include_closed=True,
                            status_ids=status_ids,
                            category_id=route["category_id"],
                            subcategory_id=route["subcategory_id"],
                            ticket_type_id=route["ticket_type_id"],
                            size=1,
                        )

                        route_total = result.get(
                            "totalElements",
                            0,
                        )

                        total += route_total

                        structured_route_totals.append(
                            {
                                "request_type": route["request_type"],
                                "total": route_total,
                            }
                        )

                else:

                    result = self.search_department_tickets(
                        department=search_department,
                        search_scope="ALL_TICKETS",
                        include_closed=True,
                        status_ids=status_ids,
                        category_id=structured_category_id,
                        subcategory_id=structured_subcategory_id,
                        ticket_type_id=structured_ticket_type_id,
                        size=1,
                    )

                    total = result.get(
                        "totalElements",
                        0,
                    )

                status_label = status_filter.replace("_", " ").title()

                return {
                    "type": "ticket_search_summary",
                    "message": (
                        "I found no matching tickets."
                        if total == 0
                        else f"I found {total} matching {ticket_word(total)}."
                    ),
                    "department": search_department,
                    "category": structured_category_name,
                    "subcategory": structured_subcategory_name,
                    "status": status_label,
                    "total": total,
                    "breakdown": [
                        {
                            "label": item["request_type"],
                            "count": item["total"],
                        }
                        for item in structured_route_totals
                    ],
                    "tickets": [],
                }

            # --------------------------------------------------
            # COUNT ONLY: ALL DEPARTMENT TICKETS BY KEYWORD
            # --------------------------------------------------
            if (
                count_only
                and search_scope == "ALL_TICKETS"
                and search_department
                and search_query
            ):
                department_config = self.get_department_search_config(
                    search_department
                )

                if not department_config:
                    return {
                        "type": "message",
                        "message": (
                            f"Ticket search for {search_department} "
                            f"is not configured yet."
                        ),
                        "total": 0,
                        "tickets": [],
                    }

                status_ids = None
                include_closed = True

                if status_filter == "OPEN":
                    include_closed = False

                elif status_filter in TICKET_STATUS_IDS:
                    status_ids = TICKET_STATUS_IDS[status_filter]

                # Get total per request type so the result card
                # can show a request-type breakdown.


                breakdown = []
                total = 0

                ticket_type_ids = department_config.get(
                    "ticket_type_ids",
                    []
                )

                for ticket_type_id in ticket_type_ids:

                    result = self.search_department_tickets(
                        department=search_department,
                        search_scope="ALL_TICKETS",
                        search_query=search_query,
                        status_ids=status_ids,
                        category_id=structured_category_id,
                        subcategory_id=structured_subcategory_id,
                        ticket_type_id=ticket_type_id,
                        include_closed=include_closed,
                        size=1,
                    )

                    request_type_total = result.get(
                        "totalElements",
                        0,
                    )

                    total += request_type_total

                    breakdown.append({
                        "label": TICKET_TYPE_NAMES.get(
                            ticket_type_id,
                            f"Request Type {ticket_type_id}",
                        ),
                        "count": request_type_total,
                    })

                return {
                    "type": "ticket_search_summary",

                    "message": (
                        f"There {'is' if total == 1 else 'are'} "
                        f"{total} "
                        f"{(status_filter.replace('_', ' ').lower() + ' ') if status_filter else ''}"
                        f"{search_department} "
                        f"{ticket_word(total)} matching "
                        f"'{search_query}'."
                    ),

                    "department": search_department,

                    "category": None,

                    "subcategory": None,
                    "keyword": search_query,

                    "status": (
                        status_filter.replace("_", " ").title()
                        if status_filter
                        else None
                    ),

                    "total": total,

                    "breakdown": breakdown,

                    "tickets": [],
                }

            # --------------------------------------------------
            # COUNT ONLY: MY IT DEPARTMENT TICKETS BY KEYWORD
            # --------------------------------------------------
            if (
                count_only
                and search_scope == "MY_TICKETS"
                and search_department == "IT Department"
                and search_query
            ):
                status_ids = None
                include_closed = True

                if status_filter == "OPEN":
                    include_closed = False

                elif status_filter in ["RESOLVED", "CLOSED", "CANCELLED"]:
                    status_id_map = {
                        "RESOLVED": [42],
                        "CLOSED": [43],
                        "CANCELLED": [44],
                    }
                    status_ids = status_id_map[status_filter]

                service_result = self.ticketing.search_my_tickets(
                    search_query=search_query,
                    requester_email=self.requester_email,
                    include_closed=include_closed,
                    status_ids=status_ids,
                    ticket_type_id=55,
                    size=1,
                )

                incident_result = self.ticketing.search_my_tickets(
                    search_query=search_query,
                    requester_email=self.requester_email,
                    include_closed=include_closed,
                    status_ids=status_ids,
                    ticket_type_id=56,
                    size=1,
                )

                service_total = service_result.get(
                    "totalElements",
                    0,
                )

                incident_total = incident_result.get(
                    "totalElements",
                    0,
                )

                total = service_total + incident_total

                return {
                    "type": "message",
                    "message": (
                        f"You have {total} IT Department "
                        f"{ticket_word(total)} matching "
                        f"'{search_query}'."
                    ),
                    "total": total,
                    "tickets": [],
                }

            # COUNT ONLY: ALL OF MY IT DEPARTMENT TICKETS
            if (
                count_only
                and search_scope == "MY_TICKETS"
                and search_department == "IT Department"
                and not status_filter
                and not search_query
            ):
                service_result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email,
                    include_closed=True,
                    ticket_type_id=55,
                    size=1,
                )

                incident_result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email,
                    include_closed=True,
                    ticket_type_id=56,
                    size=1,
                )

                service_total = service_result.get(
                    "totalElements",
                    0,
                )

                incident_total = incident_result.get(
                    "totalElements",
                    0,
                )

                total = service_total + incident_total

                return {
                    "type": "message",
                    "message": (
                        f"You have {total} IT Department "
                        f"{ticket_word(total)}."
                    ),
                    "total": total,
                    "tickets": [],
                }

            # COUNT ONLY: MY OPEN IT DEPARTMENT TICKETS
            if (
                count_only
                and search_scope == "MY_TICKETS"
                and search_department == "IT Department"
                and status_filter == "OPEN"
                and not search_query
            ):
                service_result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email,
                    include_closed=False,
                    ticket_type_id=55,
                    size=1,
                )

                incident_result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email,
                    include_closed=False,
                    ticket_type_id=56,
                    size=1,
                )

                service_total = service_result.get(
                    "totalElements",
                    0,
                )

                incident_total = incident_result.get(
                    "totalElements",
                    0,
                )

                total = service_total + incident_total

                return {
                    "type": "message",
                    "message": (
                        f"You have {total} open IT Department "
                        f"{ticket_word(total)}."
                    ),
                    "total": total,
                    "tickets": [],
                }

            # COUNT ONLY: MY IT DEPARTMENT TICKETS BY EXACT STATUS
            if (
                count_only
                and search_scope == "MY_TICKETS"
                and search_department == "IT Department"
                and status_filter in ["RESOLVED", "CLOSED", "CANCELLED"]
                and not search_query
            ):
                status_id_map = {
                    "RESOLVED": [42],
                    "CLOSED": [43],
                    "CANCELLED": [44],
                }

                status_ids = status_id_map[status_filter]

                service_result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email,
                    include_closed=True,
                    status_ids=status_ids,
                    ticket_type_id=55,
                    size=1,
                )

                incident_result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email,
                    include_closed=True,
                    status_ids=status_ids,
                    ticket_type_id=56,
                    size=1,
                )

                service_total = service_result.get(
                    "totalElements",
                    0,
                )

                incident_total = incident_result.get(
                    "totalElements",
                    0,
                )

                total = service_total + incident_total
                status_label = status_filter.lower()

                return {
                    "type": "message",
                    "message": (
                        f"You have {total} {status_label} "
                        f"IT Department {ticket_word(total)}."
                    ),
                    "total": total,
                    "tickets": [],
                }



            # COUNT ONLY: ALL OF MY TICKETS
            if (
                count_only
                and search_scope == "MY_TICKETS"
                and not status_filter
                and not search_query
            ):
                result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email,
                    include_closed=True,
                    size=1,
                )

                total = result.get("totalElements", 0)

                return {
                    "type": "message",
                    "message": (
                        f"You have {total} "
                        f"{ticket_word(total)}."
                    ),
                    "total": total,
                    "tickets": [],
                }

            # --------------------------------------------------
            # LIST: ALL IT DEPARTMENT TICKETS
            # --------------------------------------------------
            if (
                not count_only
                and search_scope == "ALL_TICKETS"
                and search_department == "IT Department"
                and not status_filter
                and not search_query
            ):
                service_result = self.ticketing.get_all_tickets(
                    include_closed=True,
                    ticket_type_id=55,
                    size=20,
                )

                incident_result = self.ticketing.get_all_tickets(
                    include_closed=True,
                    ticket_type_id=56,
                    size=20,
                )

                service_tickets = service_result.get("content", [])
                incident_tickets = incident_result.get("content", [])

                service_total = service_result.get("totalElements", 0)
                incident_total = incident_result.get("totalElements", 0)

                total = service_total + incident_total

                tickets = service_tickets + incident_tickets

                tickets.sort(
                    key=lambda ticket: ticket.get("createdAt") or "",
                    reverse=True,
                )

                tickets = tickets[:20]

                return {
                    "type": "ticket_list",
                    "message": (
                        f"I found {total} IT Department "
                        f"{ticket_word(total)}."
                    ),
                    "total": total,
                    "tickets": tickets,
                }

            # --------------------------------------------------
            # LIST: ALL IT DEPARTMENT TICKETS BY KEYWORD
            # --------------------------------------------------
            if (
                not count_only
                and search_scope == "ALL_TICKETS"
                and search_department == "IT Department"
                and search_query
            ):
                status_ids = None
                include_closed = True

                if status_filter == "OPEN":
                    include_closed = False

                elif status_filter in ["RESOLVED", "CLOSED", "CANCELLED"]:
                    status_id_map = {
                        "RESOLVED": [42],
                        "CLOSED": [43],
                        "CANCELLED": [44],
                    }
                    status_ids = status_id_map[status_filter]

                service_result = self.ticketing.search_tickets(
                    search_query=search_query,
                    include_closed=include_closed,
                    status_ids=status_ids,
                    ticket_type_id=55,
                    size=20,
                )

                incident_result = self.ticketing.search_tickets(
                    search_query=search_query,
                    include_closed=include_closed,
                    status_ids=status_ids,
                    ticket_type_id=56,
                    size=20,
                )

                service_tickets = service_result.get("content", [])
                incident_tickets = incident_result.get("content", [])

                service_total = service_result.get("totalElements", 0)
                incident_total = incident_result.get("totalElements", 0)

                total = service_total + incident_total

                tickets = service_tickets + incident_tickets

                tickets.sort(
                    key=lambda ticket: ticket.get("createdAt") or "",
                    reverse=True,
                )

                tickets = tickets[:20]

                return {
                    "type": "ticket_list",
                    "message": (
                        f"I found {total} IT Department "
                        f"{ticket_word(total)} matching "
                        f"'{search_query}'."
                    ),
                    "total": total,
                    "tickets": tickets,
                }

            # --------------------------------------------------
            # LIST: ALL OPEN IT DEPARTMENT TICKETS
            # --------------------------------------------------
            if (
                not count_only
                and search_scope == "ALL_TICKETS"
                and search_department == "IT Department"
                and status_filter == "OPEN"
                and not search_query
            ):
                service_result = self.ticketing.get_all_tickets(
                    include_closed=False,
                    ticket_type_id=55,
                    size=20,
                )

                incident_result = self.ticketing.get_all_tickets(
                    include_closed=False,
                    ticket_type_id=56,
                    size=20,
                )

                service_tickets = service_result.get("content", [])
                incident_tickets = incident_result.get("content", [])

                service_total = service_result.get("totalElements", 0)
                incident_total = incident_result.get("totalElements", 0)

                total = service_total + incident_total

                tickets = service_tickets + incident_tickets

                tickets.sort(
                    key=lambda ticket: ticket.get("createdAt") or "",
                    reverse=True,
                )

                tickets = tickets[:20]

                return {
                    "type": "ticket_list",
                    "message": (
                        f"I found {total} open IT Department "
                        f"{ticket_word(total)}."
                    ),
                    "total": total,
                    "tickets": tickets,
                }

            # --------------------------------------------------
            # LIST: MY IT DEPARTMENT TICKETS
            # --------------------------------------------------
            if (
                not count_only
                and search_scope == "MY_TICKETS"
                and search_department == "IT Department"
                and not status_filter
                and not search_query
            ):
                service_result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email,
                    include_closed=True,
                    ticket_type_id=55,
                    size=20,
                )

                incident_result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email,
                    include_closed=True,
                    ticket_type_id=56,
                    size=20,
                )

                service_tickets = service_result.get("content", [])
                incident_tickets = incident_result.get("content", [])

                service_total = service_result.get("totalElements", 0)
                incident_total = incident_result.get("totalElements", 0)

                total = service_total + incident_total

                tickets = service_tickets + incident_tickets

                tickets.sort(
                    key=lambda ticket: ticket.get("createdAt") or "",
                    reverse=True,
                )

                tickets = tickets[:20]

                return {
                    "type": "ticket_list",
                    "message": (
                        f"I found {total} of your IT Department "
                        f"{ticket_word(total)}."
                    ),
                    "total": total,
                    "tickets": tickets,
                }

            # --------------------------------------------------
            # LIST: MY OPEN IT DEPARTMENT TICKETS
            # --------------------------------------------------
            if (
                not count_only
                and search_scope == "MY_TICKETS"
                and search_department == "IT Department"
                and status_filter == "OPEN"
                and not search_query
            ):
                service_result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email,
                    include_closed=False,
                    ticket_type_id=55,
                    size=20,
                )

                incident_result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email,
                    include_closed=False,
                    ticket_type_id=56,
                    size=20,
                )

                service_tickets = service_result.get("content", [])
                incident_tickets = incident_result.get("content", [])

                service_total = service_result.get("totalElements", 0)
                incident_total = incident_result.get("totalElements", 0)

                total = service_total + incident_total

                tickets = service_tickets + incident_tickets

                tickets.sort(
                    key=lambda ticket: ticket.get("createdAt") or "",
                    reverse=True,
                )

                tickets = tickets[:20]

                return {
                    "type": "ticket_list",
                    "message": (
                        f"I found {total} of your open IT Department "
                        f"{ticket_word(total)}."
                    ),
                    "total": total,
                    "tickets": tickets,
                }

            # --------------------------------------------------
            # LIST: MY IT DEPARTMENT TICKETS BY EXACT STATUS
            # --------------------------------------------------
            if (
                not count_only
                and search_scope == "MY_TICKETS"
                and search_department == "IT Department"
                and status_filter in ["RESOLVED", "CLOSED", "CANCELLED"]
                and not search_query
            ):
                status_id_map = {
                    "RESOLVED": [42],
                    "CLOSED": [43],
                    "CANCELLED": [44],
                }

                status_ids = status_id_map[status_filter]

                service_result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email,
                    include_closed=True,
                    status_ids=status_ids,
                    ticket_type_id=55,
                    size=20,
                )

                incident_result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email,
                    include_closed=True,
                    status_ids=status_ids,
                    ticket_type_id=56,
                    size=20,
                )

                service_tickets = service_result.get("content", [])
                incident_tickets = incident_result.get("content", [])

                service_total = service_result.get("totalElements", 0)
                incident_total = incident_result.get("totalElements", 0)

                total = service_total + incident_total

                tickets = service_tickets + incident_tickets

                tickets.sort(
                    key=lambda ticket: ticket.get("createdAt") or "",
                    reverse=True,
                )

                tickets = tickets[:20]

                status_label = status_filter.lower()

                return {
                    "type": "ticket_list",
                    "message": (
                        f"I found {total} of your {status_label} "
                        f"IT Department {ticket_word(total)}."
                    ),
                    "total": total,
                    "tickets": tickets,
                }

            # --------------------------------------------------
            # LIST: MY IT DEPARTMENT TICKETS BY KEYWORD
            # --------------------------------------------------
            if (
                not count_only
                and search_scope == "MY_TICKETS"
                and search_department == "IT Department"
                and search_query
            ):
                status_ids = None
                include_closed = True

                if status_filter == "OPEN":
                    include_closed = False

                elif status_filter in ["RESOLVED", "CLOSED", "CANCELLED"]:
                    status_id_map = {
                        "RESOLVED": [42],
                        "CLOSED": [43],
                        "CANCELLED": [44],
                    }
                    status_ids = status_id_map[status_filter]

                service_result = self.ticketing.search_my_tickets(
                    search_query=search_query,
                    requester_email=self.requester_email,
                    include_closed=include_closed,
                    status_ids=status_ids,
                    ticket_type_id=55,
                    size=20,
                )

                incident_result = self.ticketing.search_my_tickets(
                    search_query=search_query,
                    requester_email=self.requester_email,
                    include_closed=include_closed,
                    status_ids=status_ids,
                    ticket_type_id=56,
                    size=20,
                )

                service_tickets = service_result.get("content", [])
                incident_tickets = incident_result.get("content", [])

                service_total = service_result.get("totalElements", 0)
                incident_total = incident_result.get("totalElements", 0)

                total = service_total + incident_total

                tickets = service_tickets + incident_tickets

                tickets.sort(
                    key=lambda ticket: ticket.get("createdAt") or "",
                    reverse=True,
                )

                tickets = tickets[:20]

                return {
                    "type": "ticket_list",
                    "message": (
                        f"I found {total} of your IT Department "
                        f"{ticket_word(total)} matching "
                        f"'{search_query}'."
                    ),
                    "total": total,
                    "tickets": tickets,
                }

            # COUNT ONLY: ALL TICKETS
            if (
                count_only
                and search_scope == "ALL_TICKETS"
                and not status_filter
                and not search_query
            ):
                result = self.ticketing.get_all_tickets(
                    include_closed=True,
                    size=1,
                )

                total = result.get("totalElements", 0)

                return {
                    "type": "message",
                    "message": (
                        f"There {'is' if total == 1 else 'are'} {total} "
                        f"{ticket_word(total)}."
                    ),
                    "total": total,
                    "tickets": [],
                }
            
            # --------------------------------------------------
            # COUNT ONLY: MY OPEN TICKETS
            # --------------------------------------------------

            if (
                count_only
                and search_scope == "MY_TICKETS"
                and status_filter == "OPEN"
                and not search_query
            ):
                result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email,
                    include_closed=False,
                    size=1,
                )

                total = result.get("totalElements", 0)

                return {
                    "type": "message",
                    "message": (
                        f"You have {total} open "
                        f"{ticket_word(total)}."
                    ),
                    "total": total,
                    "tickets": [],
                }

            # --------------------------------------------------
            # COUNT ONLY: MY TICKETS BY EXACT STATUS
            # --------------------------------------------------
            if (
                count_only
                and search_scope == "MY_TICKETS"
                and not search_department
                and status_filter in TICKET_STATUS_IDS
                and not search_query
            ):
                status_ids = TICKET_STATUS_IDS[status_filter]

                result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email,
                    include_closed=True,
                    status_ids=status_ids,
                    size=1,
                )

                total = result.get(
                    "totalElements",
                    0,
                )

                status_label = (
                    status_filter
                    .replace("_", " ")
                    .title()
                )

                return {
                    "type": "ticket_search_summary",

                    "message": (
                        "I found no matching tickets."
                        if total == 0
                        else (
                            f"I found {total} matching "
                            f"{ticket_word(total)}."
                        )
                    ),

                    "department": "My Tickets",

                    "category": None,

                    "subcategory": None,

                    "status": status_label,

                    "total": total,

                    "breakdown": [],

                    "tickets": [],
                }

            # --------------------------------------------------
            # COUNT ONLY: ALL OPEN TICKETS
            # --------------------------------------------------

            if (
                count_only
                and search_scope == "ALL_TICKETS"
                and status_filter == "OPEN"
                and not search_query
            ):
                result = self.ticketing.get_all_tickets(
                    include_closed=False,
                    size=1,
                )

                total = result.get("totalElements", 0)

                return {
                    "type": "message",
                    "message": (
                        f"There {'is' if total == 1 else 'are'} {total} open "
                        f"{ticket_word(total)}."
                    ),
                    "total": total,
                    "tickets": [],
                }

            # --------------------------------------------------
            # COUNT ONLY: ALL TICKETS BY EXACT STATUS
            # --------------------------------------------------
            if (
                count_only
                and search_scope == "ALL_TICKETS"
                and not search_department
                and status_filter in TICKET_STATUS_IDS
                and not search_query
            ):
                status_ids = TICKET_STATUS_IDS[status_filter]

                result = self.ticketing.get_all_tickets(
                    include_closed=True,
                    status_ids=status_ids,
                    size=1,
                )

                total = result.get(
                    "totalElements",
                    0,
                )

                status_label = (
                    status_filter
                    .replace("_", " ")
                    .title()
                )

                return {
                    "type": "ticket_search_summary",

                    "message": (
                        "I found no matching tickets."
                        if total == 0
                        else (
                            f"I found {total} matching "
                            f"{ticket_word(total)}."
                        )
                    ),

                    "department": None,

                    "category": None,

                    "subcategory": None,

                    "status": status_label,

                    "total": total,

                    "breakdown": [],

                    "tickets": [],
                }

            # --------------------------------------------------
            # MY OPEN TICKETS
            # --------------------------------------------------

            if (
                search_scope == "MY_TICKETS"
                and status_filter == "OPEN"
                and not search_query
            ):
                result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email,
                    include_closed=False,
                )



                tickets = result.get("content", [])

                if not tickets:
                    return {
                        "type": "ticket_status",
                        "message": "You don't have any open tickets.",
                        "total": 0,
                        "tickets": [],
                    }

                ticket_list = []

                for ticket in tickets:
                    status = ticket.get("status") or {}
                    priority = ticket.get("priority") or {}

                    ticket_list.append({
                        "ticket_number": ticket.get("ticketNumber"),
                        "title": ticket.get("title"),
                        "status": status.get("status", "Unknown"),
                        "priority": priority.get("name", "Unknown"),
                        "web_url": ticket.get("webUrl"),
                    })

                total = result.get(
                    "totalElements",
                    len(ticket_list),
                )

                return {
                    "type": "ticket_status",
                    "message": f"You have {total} open ticket(s).",
                    "total": total,
                    "tickets": ticket_list,
                }

            # --------------------------------------------------
            # MY RESOLVED / CLOSED / CANCELLED TICKETS
            # --------------------------------------------------

            if (
                search_scope == "MY_TICKETS"
                and status_filter in [
                    "RESOLVED",
                    "CLOSED",
                    "CANCELLED",
                ]
                and not search_query
            ):
                status_id_map = {
                    "RESOLVED": [42],
                    "CLOSED": [43],
                    "CANCELLED": [44],
                }

                result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email,
                    include_closed=True,
                    status_ids=status_id_map[status_filter],
                )

                tickets = result.get("content", [])

                status_label = status_filter.lower()

                if not tickets:
                    return {
                        "type": "ticket_status",
                        "message": (
                            f"You don't have any "
                            f"{status_label} tickets."
                        ),
                        "total": 0,
                        "tickets": [],
                    }

                ticket_list = []

                for ticket in tickets:
                    status = ticket.get("status") or {}
                    priority = ticket.get("priority") or {}

                    ticket_list.append({
                        "ticket_number": ticket.get("ticketNumber"),
                        "title": ticket.get("title"),
                        "status": status.get(
                            "status",
                            "Unknown"
                        ),
                        "priority": priority.get(
                            "name",
                            "Unknown"
                        ),
                        "web_url": ticket.get("webUrl"),
                    })

                total = result.get(
                    "totalElements",
                    len(ticket_list),
                )

                return {
                    "type": "ticket_status",
                    "message": (
                        f"You have {total} "
                        f"{status_label} ticket(s)."
                    ),
                    "total": total,
                    "tickets": ticket_list,
                }

            # --------------------------------------------------
            # ALL OPEN TICKETS
            # --------------------------------------------------

            if (
                search_scope == "ALL_TICKETS"
                and status_filter == "OPEN"
                and not search_query
            ):
                result = self.ticketing.get_all_tickets(
                    include_closed=False,
                )

                tickets = result.get("content", [])

                if not tickets:
                    return {
                        "type": "ticket_status",
                        "message": "I couldn't find any open tickets.",
                        "total": 0,
                        "tickets": [],
                    }

                ticket_list = []

                for ticket in tickets:
                    status = ticket.get("status") or {}
                    priority = ticket.get("priority") or {}

                    ticket_list.append({
                        "ticket_number": ticket.get("ticketNumber"),
                        "title": ticket.get("title"),
                        "status": status.get("status", "Unknown"),
                        "priority": priority.get("name", "Unknown"),
                        "web_url": ticket.get("webUrl"),
                    })

                total = result.get(
                    "totalElements",
                    len(ticket_list),
                )

                return {
                    "type": "ticket_status",
                    "message": f"I found {total} open ticket(s).",
                    "total": total,
                    "tickets": ticket_list,
                }

            # --------------------------------------------------
            # ALL TICKETS BY EXACT CLOSED STATUS
            # --------------------------------------------------

            if (
                search_scope == "ALL_TICKETS"
                and status_filter in [
                    "RESOLVED",
                    "CLOSED",
                    "CANCELLED",
                ]
                and not search_query
            ):
                status_id_map = {
                    "RESOLVED": [42],
                    "CLOSED": [43],
                    "CANCELLED": [44],
                }

                result = self.ticketing.get_all_tickets(
                    include_closed=True,
                    status_ids=status_id_map[status_filter],
                )

                tickets = result.get("content", [])

                if not tickets:
                    return {
                        "type": "ticket_status",
                        "message": (
                            f"I couldn't find any "
                            f"{status_filter.lower()} tickets."
                        ),
                        "total": 0,
                        "tickets": [],
                    }

                ticket_list = []

                for ticket in tickets:
                    status = ticket.get("status") or {}
                    priority = ticket.get("priority") or {}

                    ticket_list.append({
                        "ticket_number": ticket.get("ticketNumber"),
                        "title": ticket.get("title"),
                        "status": status.get("status", "Unknown"),
                        "priority": priority.get("name", "Unknown"),
                        "web_url": ticket.get("webUrl"),
                    })

                total = result.get(
                    "totalElements",
                    len(ticket_list),
                )

                return {
                    "type": "ticket_status",
                    "message": (
                        f"I found {total} "
                        f"{status_filter.lower()} ticket(s)."
                    ),
                    "total": total,
                    "tickets": ticket_list,
                }

            # --------------------------------------------------
            # PLAIN "ALL TICKETS" REQUEST
            # --------------------------------------------------

            if (
                search_scope == "ALL_TICKETS"
                and not search_query
                and not status_filter
            ):
                result = self.ticketing.get_all_tickets(
                    include_closed=True,
                )

                tickets = result.get("content", [])

                if not tickets:
                    return {
                        "type": "ticket_status",
                        "message": "I couldn't find any tickets.",
                        "total": 0,
                        "tickets": [],
                    }

                ticket_list = []

                for ticket in tickets:
                    status = ticket.get("status") or {}
                    priority = ticket.get("priority") or {}

                    ticket_list.append({
                        "ticket_number": ticket.get("ticketNumber"),
                        "title": ticket.get("title"),
                        "status": status.get(
                            "status",
                            "Unknown",
                        ),
                        "priority": priority.get(
                            "name",
                            "Unknown",
                        ),
                        "web_url": ticket.get("webUrl"),
                    })

                total = result.get(
                    "totalElements",
                    len(ticket_list),
                )

                return {
                    "type": "ticket_status",
                    "message": f"I found {total} ticket(s).",
                    "total": total,
                    "tickets": ticket_list,
                }

            # No text query and no supported structured filter
            if not search_query:
                return {
                    "type": "message",
                    "message": "What would you like me to search for?"
                }

            # --------------------------------------------------
            # PLAIN "MY TICKETS" REQUEST
            # --------------------------------------------------

            if (
                search_scope == "MY_TICKETS"
                and str(search_query).strip().lower()
                in ["ticket", "tickets", "my ticket", "my tickets"]
            ):
                result = self.ticketing.get_my_tickets(
                    requester_email=self.requester_email
                )

                tickets = result.get("content", [])

                if not tickets:
                    return {
                        "type": "ticket_status",
                        "message": "I couldn't find any tickets for you.",
                        "tickets": [],
                    }

                ticket_list = []

                for ticket in tickets:
                    status = ticket.get("status") or {}
                    priority = ticket.get("priority") or {}

                    ticket_list.append({
                        "ticket_number": ticket.get("ticketNumber"),
                        "title": ticket.get("title"),
                        "status": status.get("status", "Unknown"),
                        "priority": priority.get("name", "Unknown"),
                        "web_url": ticket.get("webUrl"),
                    })

                total = result.get(
                    "totalElements",
                    len(ticket_list)
                )

                return {
                    "type": "ticket_status",
                    "message": f"You have {total} ticket(s).",
                    "total": total,
                    "tickets": ticket_list,
                }


            # --------------------------------------------------
            # SEARCH MY TICKETS
            # --------------------------------------------------
            if search_scope == "MY_TICKETS":

                status_ids = None

                if status_filter == "RESOLVED":
                    status_ids = [42]

                elif status_filter == "CLOSED":
                    status_ids = [43]

                elif status_filter == "CANCELLED":
                    status_ids = [44]

                if count_only:
                    result = self.ticketing.search_my_tickets(
                        search_query=search_query,
                        requester_email=self.requester_email,
                        include_closed=(
                            False
                            if status_filter == "OPEN"
                            else True
                        ),
                        status_ids=status_ids,
                        size=1,
                    )

                    total = result.get("totalElements", 0)

                    status_label = ""

                    if status_filter == "OPEN":
                        status_label = "open "
                    elif status_filter == "RESOLVED":
                        status_label = "resolved "
                    elif status_filter == "CLOSED":
                        status_label = "closed "
                    elif status_filter == "CANCELLED":
                        status_label = "cancelled "

                    return {
                        "type": "message",
                        "message": (
                            f"You have {total} "
                            f"{status_label}{search_query} "
                            f"{ticket_word(total)}."
                        ),
                        "total": total,
                        "tickets": [],
                    }


                result = self.ticketing.search_my_tickets(
                    search_query=search_query,
                    requester_email=self.requester_email,
                    include_closed=(
                        False
                        if status_filter == "OPEN"
                        else True
                    ),
                    status_ids=status_ids,
                )

            # --------------------------------------------------
            # SEARCH ALL TICKETS
            # --------------------------------------------------
            else:
                status_ids = None

                if status_filter == "RESOLVED":
                    status_ids = [42]
                elif status_filter == "CLOSED":
                    status_ids = [43]
                elif status_filter == "CANCELLED":
                    status_ids = [44]

                if count_only:
                    result = self.ticketing.search_tickets(
                        search_query=search_query,
                        include_closed=(
                            False
                            if status_filter == "OPEN"
                            else True
                        ),
                        status_ids=status_ids,
                        size=1,
                    )

                    total = result.get("totalElements", 0)

                    status_label = ""

                    if status_filter == "OPEN":
                        status_label = "open "
                    elif status_filter == "RESOLVED":
                        status_label = "resolved "
                    elif status_filter == "CLOSED":
                        status_label = "closed "
                    elif status_filter == "CANCELLED":
                        status_label = "cancelled "

                    return {
                        "type": "message",
                        "message": (
                            f"There {'is' if total == 1 else 'are'} {total} "
                            f"{status_label}{search_query} "
                            f"{ticket_word(total)}."
                        ),
                        "total": total,
                        "tickets": [],
                    }


                result = self.ticketing.search_tickets(
                    search_query=search_query,
                    include_closed=(
                        False
                        if status_filter == "OPEN"
                        else True
                    ),
                    status_ids=status_ids,
                )

            tickets = result.get("content", [])

            if not tickets:
                scope_text = (
                    "your"
                    if search_scope == "MY_TICKETS"
                    else "all"
                )

                return {
                    "type": "ticket_search",
                    "message": (
                        f"I couldn't find any {scope_text} tickets "
                        f"related to '{search_query}'."
                    ),
                    "search_query": search_query,
                    "search_scope": search_scope,
                    "tickets": []
                }

            ticket_list = []

            for ticket in tickets:
                status = ticket.get("status") or {}
                priority = ticket.get("priority") or {}

                ticket_list.append({
                    "ticket_number": ticket.get("ticketNumber"),
                    "title": ticket.get("title"),
                    "status": status.get("status", "Unknown"),
                    "priority": priority.get("name", "Unknown"),
                    "web_url": ticket.get("webUrl"),
                })

            total = result.get(
                "totalElements",
                len(ticket_list)
            )

            status_label = ""

            if status_filter == "OPEN":
                status_label = "open "
            elif status_filter == "RESOLVED":
                status_label = "resolved "
            elif status_filter == "CLOSED":
                status_label = "closed "
            elif status_filter == "CANCELLED":
                status_label = "cancelled "

            if search_scope == "MY_TICKETS":
                message = (
                    f"I found {total} of your "
                    f"{status_label}ticket(s) "
                    f"related to '{search_query}'."
                )
            else:
                message = (
                    f"I found {total} "
                    f"{status_label}ticket(s) "
                    f"related to '{search_query}'."
                )

            return {
                "type": "ticket_search",
                "message": message,
                "search_query": search_query,
                "search_scope": search_scope,
                "total": total,
                "tickets": ticket_list
            }

        except Exception as e:
            print("TICKET SEARCH ERROR:", str(e))

            return {
                "type": "error",
                "message": "I couldn't search the ticketing system."
            }           

    def confirm_ticket(self):

        if not self.state.is_complete():

            return {
                "type": "message",
                "message": (
                    "Some ticket information is still missing."
                ),
                "missing_fields": self.state.get_missing_fields(),
            }

        try:

            result = self.ticketing.create_ticket(

                category=self.state.selected_category,

                subcategory=self.state.subcategory,

                description=self.state.description,

                location=self.state.location,

                priority=self.state.priority,

                requester=self.requester_email,
                actor=self.actor_email,

                impact=(
                    self.state.impact
                    if self.state.request_type == "Incident Request"
                    else None
                ),

                start_date=(
                    self.state.start_time.split("T")[0]
                    if (
                        self.state.request_type == "Incident Request"
                        and self.state.start_time
                    )
                    else None
                ),

                target_date=(
                    self.state.target_date
                    if self.state.request_type == "Service Request"
                    else None
                ),

                business_justification=(
                    self.state.business_justification
                    if self.state.request_type == "Service Request"
                    else None
                ),

                urgency=(
                    self.state.urgency
                    if (
                        self.state.department == "HR Department"
                        and self.state.request_type == "Service Request"
                    )
                    else None
                ),

                email=(
                    self.state.email
                    if (
                        self.state.department == "IT Department"
                        and self.state.request_type in [
                            "Service Request",
                            "Incident Request",
                        ]
                    )
                    else None
                ),

                phone=(
                    self.state.phone
                    if (
                        self.state.department == "IT Department"
                        and self.state.request_type in [
                            "Service Request",
                            "Incident Request",
                        ]
                    )
                    else None
                ),

                request_type=self.state.request_type,

                department=self.state.department,
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
                "message": "The ticket could not be created.",
                "details": result,
                "options": [
                    "Confirm & Create Ticket",
                    "Cancel",
                ],
            }

        except Exception as e:

            print("TICKET CREATION ERROR:", str(e))

            return {
                "type": "error",
                "message": (
                    "I couldn't create the ticket in the "
                    "Service Excellence Portal."
                ),
                "details": str(e),
                "options": [
                    "Confirm & Create Ticket",
                    "Cancel",
                ],
            }
        
    def cancel(self):

        self.state.reset()

        return {
            "type": "message",
            "message": "Ticket creation cancelled.",
        }
