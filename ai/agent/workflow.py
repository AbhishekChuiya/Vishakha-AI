from ai.agent.conversation import ConversationState
from ai.agent.orchestrator import AgentOrchestrator
from ai.tools.ticketing.ticketing_tool import TicketingTool
from ai.tools.ticketing.routing import get_departments
from ai.agent.config import REQUEST_TYPES, LOCATIONS
from ai.agent.catalog import CATEGORIES, SUBCATEGORY_REQUEST_TYPES
from datetime import datetime, timedelta
from django.utils import timezone


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

        # ----------------------------------------------
        # HANDLE ANSWER TO CURRENT QUESTION
        # ----------------------------------------------

        if self.state.current_question:
            return self.handle_option(user_message)

        agent_result = self.orchestrator.understand_request(
            user_message,
            current_ticket_number=self.state.ticket_number
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
                "message": "Which department is this request for?",
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
                "message": "What type of request would you like to create?",
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

            self.state.current_question = "category"

            return {
                "type": "question",
                "field": "category",
                "message": (
                    "Which category is this request related to?"
                ),
                "options": list(department_categories.keys()),
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

        if not self.state.subcategory:

            if not category_subcategories:

                return {
                    "type": "message",
                    "message": (
                        f"No subcategories are configured for "
                        f"{selected_category}."
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
                "options": category_subcategories,
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
        # STEP 7: Target Date (Service Requests only)
        # ----------------------------------------------

        if self.state.request_type == "Service Request":

            if not getattr(self.state, "target_date", None):

                self.state.current_question = "target_date"

                return {
                    "type": "question",
                    "field": "target_date",
                    "message": "When do you need this service or requirement completed?",
                    "input_type": "date",
                    "placeholder": "Select target date",
                }

        # ----------------------------------------------
        # Business Justification (Service Requests only)
        # ----------------------------------------------

        if self.state.request_type == "Service Request":

            if not getattr(self.state, "business_justification", None):

                self.state.current_question = "business_justification"

                return {
                    "type": "question",
                    "field": "business_justification",
                    "message": "Why is this service or requirement needed? Please provide the business justification.",
                    "input_type": "text",
                    "placeholder": "Enter the business justification...",
                }

        # ----------------------------------------------
        # STEP 7: Impact (Incident Requests only)
        # ----------------------------------------------

        if self.state.request_type == "Incident Request":

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

            if option == "Cancel":
                return self.cancel()

            return {
                "type": "message",
                "message": (
                    "Please select either "
                    "'Confirm & Create Ticket' or 'Cancel'."
                ),
                "options": [
                    "Confirm & Create Ticket",
                    "Cancel",
                ],
            }

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

            self.state.request_type = option
            self.state.current_question = None

            return self.handle_create_ticket()

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
            if not self.state.search_query:
                return {
                    "type": "message",
                    "message": "What would you like me to search for?"
                }

            search_query = self.state.search_query
            search_scope = self.state.search_scope

            # --------------------------------------------------
            # SEARCH MY TICKETS
            # --------------------------------------------------
            if search_scope == "MY_TICKETS":
                result = self.ticketing.search_my_tickets(
                    search_query=search_query
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