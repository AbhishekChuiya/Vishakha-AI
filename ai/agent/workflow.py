from ai.agent.conversation import ConversationState
from ai.agent.orchestrator import AgentOrchestrator
from ai.tools.ticketing.ticketing_tool import TicketingTool
from ai.tools.ticketing.routing import get_departments
from ai.agent.config import REQUEST_TYPES, LOCATIONS
from ai.agent.catalog import CATEGORIES, SUBCATEGORY_REQUEST_TYPES
from datetime import datetime, timedelta
from django.utils import timezone


class AgentWorkflow:

    def __init__(
        self,
        state=None,
        requester_email=None,
    ):

        self.orchestrator = AgentOrchestrator()

        self.ticketing = TicketingTool()

        self.requester_email = requester_email

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
    
    def handle_search_tickets(self):
        try:
            search_query = self.state.search_query
            search_scope = self.state.search_scope
            status_filter = getattr(
                self.state,
                "ticket_status_filter",
                None,
            )

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
                result = self.ticketing.search_my_tickets(
                    search_query=search_query,
                    requester_email=self.requester_email,
                    include_closed=(
                        False
                        if status_filter == "OPEN"
                        else True
                    ),
                )

            # --------------------------------------------------
            # SEARCH ALL TICKETS
            # --------------------------------------------------
            else:
                result = self.ticketing.search_tickets(
                    search_query=search_query
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

            if search_scope == "MY_TICKETS":
                message = (
                    f"I found {total} of your ticket(s) "
                    f"related to '{search_query}'."
                )
            else:
                message = (
                    f"I found {total} ticket(s) "
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