class ConversationState:

    def __init__(self):
        self.reset()

    def reset(self):
        self.intent = None
        self.category = None
        self.description = None
        self.location = None
        self.priority = None
        self.ticket_number = None
        self.ticket_query = None
        self.search_query = None
        self.current_question = None
        self.status = "idle"
        self.search_scope = None

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

        if data.get("search_query"):
            self.search_query = data["search_query"]
        if data.get("search_scope"):
            self.search_scope = data["search_scope"]

    def get_missing_fields(self):

        missing = []

        if not self.category:
            missing.append("category")

        if not self.description:
            missing.append("description")

        if not self.location:
            missing.append("location")

        if not self.priority:
            missing.append("priority")

        return missing

    def is_complete(self):

        return len(self.get_missing_fields()) == 0

    def get_summary(self):

        return {
            "category": self.category,
            "description": self.description,
            "location": self.location,
            "priority": self.priority,
        }

    # =====================================================
    # SESSION SERIALIZATION
    # =====================================================

    def to_dict(self):
        return {
            "intent": self.intent,
            "category": self.category,
            "description": self.description,
            "location": self.location,
            "priority": self.priority,
            "ticket_number": self.ticket_number,
            "ticket_query": self.ticket_query,
            "search_query": self.search_query,
            "current_question": self.current_question,
            "status": self.status,
            "search_scope": self.search_scope,
        }

    def from_dict(self, data):
        if not data:
            return

        self.intent = data.get("intent")
        self.category = data.get("category")
        self.description = data.get("description")
        self.location = data.get("location")
        self.priority = data.get("priority")
        self.ticket_number = data.get("ticket_number")
        self.ticket_query = data.get("ticket_query")
        self.search_query = data.get("search_query")
        self.current_question = data.get("current_question")
        self.status = data.get("status", "idle")
        self.search_scope = data.get("search_scope")