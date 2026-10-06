
class ConversationState:

    def __init__(self):
        self.reset()

    def reset(self):
        self.intent = None
        self.department = None
        self.request_type = None

        self.category = None
        self.selected_category = None
        self.subcategory = None
        self.description = None
        self.location = None
        self.priority = None

        self.impact = None
        self.start_time = None
        self.target_date = None
        self.business_justification = None
        self.urgency = None

        self.email = None
        self.phone = None

        self.ticket_number = None
        self.ticket_query = None
        self.search_query = None
        self.search_scope = None
        self.search_department = None
        self.ticket_status_filter = None
        self.ticket_count_only = False

        self.current_question = None
        self.status = "idle"

    def update_from_agent(self, data):
        self.intent = data.get("intent")

        if data.get("category"):
            self.category = data["category"]

        if data.get("description"):
            self.description = data["description"]

        if data.get("location"):
            self.location = data["location"]

        if data.get("priority"):
            self.priority = data["priority"]

        if data.get("ticket_number"):
            self.ticket_number = data["ticket_number"]

        if data.get("ticket_query"):
            self.ticket_query = data["ticket_query"]

        if "search_query" in data:
            self.search_query = data.get("search_query")

        if "search_scope" in data:
            self.search_scope = data.get("search_scope")

        if "search_department" in data:
            self.search_department = data.get(
                "search_department"
            )

        if "ticket_status_filter" in data:
            self.ticket_status_filter = data.get("ticket_status_filter")

        if "ticket_count_only" in data:
            self.ticket_count_only = bool(
                data.get("ticket_count_only")
            )

        if data.get("department"):
            self.department = data["department"]

        if data.get("request_type"):
            self.request_type = data["request_type"]

    def get_missing_fields(self):
        missing = []

        # Department is required for Excel-based ticket routing
        if not self.department:
            missing.append("department")

        # Common fields
        if not self.selected_category:
            missing.append("category")

        if not self.subcategory:
            missing.append("subcategory")

        if not self.description:
            missing.append("description")

        if not self.location:
            missing.append("location")

        if not self.priority:
            missing.append("priority")

        # Incident Request fields
        if self.request_type == "Incident Request":

            # IT Incident Request (ticket type 56) does not use
            # Impact or Incident Start Time.
            if self.department != "IT Department":

                if not self.impact:
                    missing.append("impact")

                if not self.start_time:
                    missing.append("start_time")

        # Service Request fields
        elif self.request_type == "Service Request":

            # Strategy Service Request (ticket type 60) does not
            # have Target Date or Business Justification.
            if self.department != "Strategy":

                if not self.target_date:
                    missing.append("target_date")

                if not self.business_justification:
                    missing.append("business_justification")

            # HR Service Request requires Urgency.
            if self.department == "HR Department":
                if not self.urgency:
                    missing.append("urgency")

        # IT Service Request and Incident Request require contact details
        if (
            self.department == "IT Department"
            and self.request_type in ["Service Request", "Incident Request"]
        ):
            if not self.email:
                missing.append("email")

            if not self.phone:
                missing.append("phone")

        return missing

    def is_complete(self):
        return len(self.get_missing_fields()) == 0

    def get_summary(self):
        return {
            "request_type": self.request_type,
            "department": self.department,
            "category": self.selected_category,
            "subcategory": self.subcategory,
            "description": self.description,
            "location": self.location,
            "priority": self.priority,
            "impact": (
                self.impact
                if self.request_type == "Incident Request"
                else None
            ),
            "start_time": (
                self.start_time
                if self.request_type == "Incident Request"
                else None
            ),
            "target_date": (
                self.target_date
                if self.request_type == "Service Request"
                else None
            ),
            "business_justification": (
                self.business_justification
                if self.request_type == "Service Request"
                else None
            ),
            "urgency": (
                self.urgency
                if (
                    self.department == "HR Department"
                    and self.request_type == "Service Request"
                )
                else None
            ),
            "email": (
                self.email
                if (
                    self.department == "IT Department"
                    and self.request_type in [
                        "Service Request",
                        "Incident Request",
                    ]
                )
                else None
            ),

            "phone": (
                self.phone
                if (
                    self.department == "IT Department"
                    and self.request_type in [
                        "Service Request",
                        "Incident Request",
                    ]
                )
                else None
            ),
        }

    # SESSION SERIALIZATION

    def to_dict(self):
        return {
            "intent": self.intent,
            "department": self.department,
            "request_type": self.request_type,
            "category": self.category,
            "selected_category": self.selected_category,
            "subcategory": self.subcategory,
            "description": self.description,
            "location": self.location,
            "priority": self.priority,
            "impact": self.impact,
            "start_time": self.start_time,
            "target_date": self.target_date,
            "business_justification": self.business_justification,
            "urgency": self.urgency,
            "email": self.email,
            "phone": self.phone,
            "ticket_number": self.ticket_number,
            "ticket_query": self.ticket_query,
            "search_query": self.search_query,
            "search_scope": self.search_scope,
            "search_department": self.search_department,
            "ticket_status_filter": self.ticket_status_filter,
            "ticket_count_only": self.ticket_count_only,
            "current_question": self.current_question,
            "status": self.status,
        }

    def from_dict(self, data):
        if not data:
            return

        self.intent = data.get("intent")
        self.department = data.get("department")
        self.request_type = data.get("request_type")

        self.category = data.get("category")
        self.selected_category = data.get("selected_category")
        self.subcategory = data.get("subcategory")
        self.description = data.get("description")
        self.location = data.get("location")
        self.priority = data.get("priority")

        self.impact = data.get("impact")
        self.start_time = data.get("start_time")
        self.target_date = data.get("target_date")
        self.business_justification = data.get(
            "business_justification"
        )
        self.urgency = data.get("urgency")

        self.email = data.get("email")
        self.phone = data.get("phone")

        self.ticket_number = data.get("ticket_number")
        self.ticket_query = data.get("ticket_query")
        self.search_query = data.get("search_query")
        self.search_scope = data.get("search_scope")
        self.search_department = data.get("search_department")
        self.ticket_status_filter = data.get("ticket_status_filter")
        self.ticket_count_only = bool(
            data.get("ticket_count_only", False)
        )

        self.current_question = data.get("current_question")
        self.status = data.get("status", "idle")