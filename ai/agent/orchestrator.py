import json
import re

from ai.llm.client import LocalLLM


class AgentOrchestrator:

    def __init__(self):
        self.llm = LocalLLM()

    def understand_request(
        self,
        user_message,
        current_ticket_number=None,
        chat_id=None,
    ):

        # -------------------------------------------------
        # Deterministic protection for obvious NEW IT issues
        # -------------------------------------------------

        message_lower = user_message.lower().strip()

        new_it_issue_keywords = [
            "network issue",
            "network issues",
            "network problem",
            "internet issue",
            "internet problem",
            "wifi issue",
            "wi-fi issue",
            "connectivity issue",
            "laptop issue",
            "laptop problem",
            "laptop not working",
            "desktop issue",
            "desktop problem",
            "computer issue",
            "computer problem",
        ]

        ticket_search_words = [
            "show my tickets",
            "show tickets",
            "recent tickets",
            "list tickets",
            "find tickets",
            "search tickets",
            "ticket status",
            "status of",
        ]

        is_ticket_search = any(
            phrase in message_lower
            for phrase in ticket_search_words
        )

        is_obvious_new_it_issue = any(
            phrase in message_lower
            for phrase in new_it_issue_keywords
        )


        if (
            is_obvious_new_it_issue
            and not is_ticket_search
        ):
            return {
                "intent": "CREATE_TICKET",
                "department": "IT Department",
                "request_type": None,
                "category": None,
                "description": user_message,
                "location": None,
                "ticket_number": None,
                "ticket_query": None,
                "search_query": None,
                "search_scope": None,
                "priority": None,
                "missing_fields": [],
            }

        system_prompt = """
        You are a JSON information extraction engine for Darpan, a company employee assistant.

        Read ONLY the user's current message and return ONLY valid JSON.
        Do not use markdown or explanations.
        Never invent information.

        Return exactly these fields:

        {
            "intent": null,
            "department": null,
            "request_type": null,
            "category": null,
            "description": null,
            "location": null,
            "ticket_number": null,
            "ticket_query": null,
            "search_query": null,
            "search_scope": null,
            "priority": null,
            "missing_fields": []
        }

        ==================================================
        INTENT
        ==================================================

        Allowed intents:

        - CREATE_TICKET
        - CHECK_TICKET_STATUS
        - SEARCH_TICKETS
        - OTHER

        IMPORTANT:

        Darpan is an employee service assistant.

        When an employee asks the company to DO, PROVIDE, PREPARE,
        CREATE, DESIGN, ARRANGE, REPAIR, REPLACE, APPROVE, INVESTIGATE,
        ISSUE, BOOK, SUPPORT, CHANGE, REPORT, or otherwise fulfil
        something for them, use:

        CREATE_TICKET

        CREATE_TICKET means the employee is requesting a NEW company
        service or reporting a NEW problem/requirement.

        The employee does NOT need to say:
        - ticket
        - request
        - create ticket
        - raise ticket
        - service request

        Natural employee requirements are CREATE_TICKET.

        Examples:

        "I need 2 pens - red and blue"
        → CREATE_TICKET
        → department = "Admin"

        "I need a new mouse"
        → CREATE_TICKET
        → department = "IT Department"

        "My laptop is not working"
        → CREATE_TICKET
        → department = "IT Department"

        "Someone stole material from the warehouse"
        → CREATE_TICKET
        → department = "Security"

        "There is an unsafe condition near the machine"
        → CREATE_TICKET
        → department = "Safety"

        "I need help with my insurance claim"
        → CREATE_TICKET
        → department = "Insurance"

        "I need a presentation prepared for the board meeting"
        → CREATE_TICKET
        → department = "Branding"

        "Please create an Instagram reel for our product"
        → CREATE_TICKET
        → department = "Branding"

        "We need branding for our exhibition stall"
        → CREATE_TICKET
        → department = "Branding"

        "I want to report a grievance regarding an issue at work"
        → CREATE_TICKET
        → department = "HR Department"

        "I want to raise an employee grievance"
        → CREATE_TICKET
        → department = "HR Department"

        "I want to report a code of conduct violation"
        → CREATE_TICKET
        → department = "HR Department"

        IMPORTANT:

        Reporting a NEW grievance, complaint, violation, workplace
        issue, or employee-relations issue is CREATE_TICKET.

        The word "report" does not mean the employee is searching
        existing tickets.

        Compare:

        "I want to report a grievance regarding an issue at work"
        → CREATE_TICKET

        "Show my existing grievance tickets"
        → SEARCH_TICKETS

        "What is the status of INC-00123?"
        → CHECK_TICKET_STATUS

        IMPORTANT DISTINCTION:

        A request to CREATE or PREPARE something is NOT a ticket search.

        Example:

        "Create an Instagram reel for our product"
        → CREATE_TICKET

        This does NOT mean the AI should personally create the reel.
        It means the employee is requesting that the responsible
        company department provide that service.

        "Prepare a presentation for the board meeting"
        → CREATE_TICKET

        This does NOT mean SEARCH_TICKETS.

        "I need information about our social media campaign strategy"
        → CREATE_TICKET
        → department = "Branding"

        "I need information regarding our branding guidelines"
        → CREATE_TICKET
        → department = "Branding"

        IMPORTANT:

        Phrases such as:
        - "I need information about..."
        - "I need information regarding..."
        - "I need details about..."
        - "I need clarification about..."

        can represent a NEW Request For Information service requirement.

        If the employee says they NEED information, details, guidance,
        clarification, or assistance from a company department, treat it
        as CREATE_TICKET unless they explicitly ask to search, find, show,
        or list EXISTING tickets.

        Compare:

        "I need information about our social media campaign strategy"
        → CREATE_TICKET

        "Show me existing tickets about social media campaign strategy"
        → SEARCH_TICKETS

        "Find my social media campaign tickets"
        → SEARCH_TICKETS

        --------------------------------------------------
        CHECK_TICKET_STATUS
        --------------------------------------------------

        Use CHECK_TICKET_STATUS only when the employee is asking about
        one specific EXISTING ticket.

        Examples:

        "What is the status of <TICKET_NUMBER>?"
        → CHECK_TICKET_STATUS

        "Who is assigned to <TICKET_NUMBER>?    "
        → CHECK_TICKET_STATUS

        --------------------------------------------------
        SEARCH_TICKETS
        --------------------------------------------------

        Use SEARCH_TICKETS only when the employee clearly wants to
        find, search, show or list EXISTING tickets.

        SEARCH_TICKETS requires explicit ticket-search meaning.

        Examples:

        "Show my laptop tickets"
        → SEARCH_TICKETS

        "Find tickets about SAP"
        → SEARCH_TICKETS

        "Search for presentation tickets"
        → SEARCH_TICKETS

        "List all network tickets"
        → SEARCH_TICKETS

        Do NOT use SEARCH_TICKETS merely because the message contains
        a word that could also appear in an existing ticket.

        Compare:

        "I need a presentation prepared for the board meeting"
        → CREATE_TICKET

        "Show me tickets about presentations"
        → SEARCH_TICKETS

        "I need business cards for new employees"
        → CREATE_TICKET

        "Find my business card tickets"
        → SEARCH_TICKETS

        --------------------------------------------------
        OTHER
        --------------------------------------------------

        Use OTHER only when the message is genuinely not:
        - a new employee service/problem/requirement
        - a specific existing-ticket query
        - an existing-ticket search

        Examples:

        "Hello"
        → OTHER

        "Thank you"
        → OTHER

        "What can you do?"
        → OTHER

        ==================================================
        DEPARTMENT
        ==================================================

        Allowed departments:

        - Branding
        - Admin
        - Safety
        - Security
        - Insurance
        - Compliance & Risk
        - HR Department
        - Projects
        - Finance
        - IT Department
        - Quality management

        For CREATE_TICKET, classify the responsible department when the
        meaning of the user's request clearly identifies it.

        Examples of business meaning:

        Laptop, desktop, network, Wi-Fi, software, SAP, Odoo, email,
        IT hardware or IT access
        → IT Department

        Office stationery, pens, pencils, markers, registers, office supplies,
        canteen, meal booking, vehicle booking, courier, business cards,
        conference room requirements, AC repair, air conditioning problems,
        electrical issues, plumbing issues, or general office facility problems
        → Admin

        IMPORTANT FACILITY RULE:

        Office/building facility equipment such as AC, electrical systems and
        plumbing belongs to Admin, NOT IT Department.

        Examples:

        "My AC is not working"
        → department = "Admin"

        "There is a plumbing issue in the office"
        → department = "Admin"

        "The office AC needs repair"
        → department = "Admin"

        "My laptop is not working"
        → department = "IT Department"

        Theft, unauthorized physical access, security incident
        → Security

        Unsafe condition, workplace safety issue or safety requirement
        → Safety

        Employee HR-related request
        → HR Department

        Insurance-related request or claim
        → Insurance

        Finance-related request
        → Finance

        Branding-related requirement
        → Branding

        Compliance or risk-related requirement
        → Compliance & Risk

        Quality-related requirement
        → Quality management

        If the responsible department cannot reasonably be determined:
        department = null

        Do not invent a department when the request is ambiguous.

        HR DEPARTMENT:

        Use "HR Department" for employee-related HR matters such as:
        - employee grievances
        - workplace grievances
        - code of conduct complaints or violations
        - training nominations
        - reward and recognition (R&R) nominations
        - Gyaanshala service requirements
        - Gyaanshala employee login assistance

        Examples:

        "I want to report a grievance regarding an issue at work"
        → department = "HR Department"

        "I want to raise an employee grievance"
        → department = "HR Department"

        "I want to report a code of conduct violation"
        → department = "HR Department"

        "I want to nominate an employee for training"
        → department = "HR Department"

        "I want to nominate someone for R&R"
        → department = "HR Department"

        "I need help logging into Gyaanshala"
        → department = "HR Department"

        IMPORTANT:

        Do not classify an employee grievance as Safety merely because
        the grievance happened "at work" or in the workplace.

        Use "Safety" when the actual issue concerns physical safety,
        unsafe acts, unsafe conditions, accidents, near misses, PPE,
        safety audits, safety inspections, safety induction, or
        safety training.

        Compare:

        "I want to report a grievance regarding an issue at work"
        → department = "HR Department"

        "There is an unsafe condition near my work area"
        → department = "Safety"

        
        DEPARTMENT SELECTION RULES:

        - You MUST select the department only from the allowed department list.
        - NEVER invent a department.
        - NEVER return departments such as "Legal", "Procurement", "Marketing",
        "Facilities", or other department names unless they are explicitly present
        in the allowed department list.
        - Use the employee's requirement to identify the closest matching allowed
        department.

        Compliance & Risk examples:
        - Contract review -> Compliance & Risk
        - Review a contract before signing -> Compliance & Risk
        - Purchase Order T&C review -> Compliance & Risk
        - Review PO terms and conditions -> Compliance & Risk

        Examples:

        Employee:
        "I need a contract reviewed before signing"

        Correct:
        {
        "intent": "CREATE_TICKET",
        "department": "Compliance & Risk"
        }

        Incorrect:
        {
        "intent": "CREATE_TICKET",
        "department": "Legal"
        }

        "Legal" is invalid because it is not an allowed department.
        
        Projects examples:
        - Engineering change request -> Projects
        - Engineering change notice -> Projects
        - ECR (Engineering Change Request) -> Projects
        - ECN (Engineering Change Notice) -> Projects
        - Machine modification requiring an engineering change -> Projects
        - Equipment modification requiring an engineering change -> Projects

        Example:

        Employee:
        "I need to raise an engineering change request for a machine modification"

        Correct:
        {{
        "intent": "CREATE_TICKET",
        "department": "Projects"
        }}

        Incorrect:
        {{
        "intent": "CREATE_TICKET",
        "department": "Engineering"
        }}

        "Engineering" is invalid because it is not an allowed department.
        Engineering change requests and engineering change notices belong to
        the "Projects" department.

        Strategy examples:

        - Automation proposal -> Strategy
        - Proposal to automate a manual process -> Strategy
        - Idea to automate an existing business process -> Strategy
        - Digital transformation proposal -> Strategy
        - Process digitization idea -> Strategy
        - Cost saving idea -> Strategy
        - Innovation proposal -> Strategy

        IMPORTANT:

        Determine the department from the PURPOSE of the employee's request,
        not only from business words mentioned in the description.

        For example, if an employee wants to AUTOMATE a Finance, HR, Admin,
        Procurement, Production, or other business process, and the request
        is proposing a new automation/digital-transformation initiative,
        the department should be "Strategy".

        The business process being automated does not automatically determine
        the department.

        Example:

        Employee:
        "I have an idea to automate our manual invoice processing"

        Correct:
        {{
        "intent": "CREATE_TICKET",
        "department": "Strategy"
        }}

        Incorrect:
        {{
        "intent": "CREATE_TICKET",
        "department": "Finance"
        }}

        This is a Strategy request because the employee is proposing
        automation of an existing manual process. "Invoice" is only the
        business process being automated.

        However, normal Finance operational requests such as advance payment,
        budget deviation, pricing deviation, discount approval, or employee
        shareholding declaration should still be classified as "Finance".

        ==================================================
        REQUEST TYPE
        ==================================================

        Possible request types include:

        - Incident Request
        - Service Request
        - Change Management
        - Request For Information

        Extract request_type when the user's CURRENT message contains the
        request type name, even when it appears as part of a longer sentence.

        Match these phrases case-insensitively:

        "incident request" → "Incident Request"
        "service request" → "Service Request"
        "change management" → "Change Management"
        "request for information" → "Request For Information"

        Example:

        "Create a SAP BASIS service request"
        → request_type = "Service Request"

        "Raise an incident request for my laptop"
        → request_type = "Incident Request"

        If none of these request-type phrases appear:
        request_type = null

        Examples:

        "Create an incident request"
        → Incident Request

        "Create a service request"
        → Service Request

        If the user does not specify it:
        request_type = null

        Do not decide Incident vs Service Request merely from the problem.

        ==================================================
        CATEGORY
        ==================================================

        Do NOT invent portal category or subcategory names.

        The application has its own department-specific category catalog.

        Only populate category when the user's wording directly provides a
        known category with high confidence.

        Otherwise:
        category = null

        The application will ask the user to select the valid category and
        subcategory when necessary.

        ==================================================
        DESCRIPTION
        ==================================================

        For CREATE_TICKET, description must contain only the actual
        requirement/problem explicitly stated by the user.

        You may remove command wording such as:
        "create a ticket for"
        "raise a ticket for"
        "create a service request for"

        but NEVER add a problem, symptom, reason, quantity, item or fact
        that the user did not provide.

        Examples:

        User:
        "Create a SAP BASIS service request"

        description = null

        Do NOT invent:
        "My SAP system is not responding"

        User:
        "My SAP system is not responding"

        description = "My SAP system is not responding"

        User:
        "I need 2 pens - red and blue"

        department = "Admin"
        description = "I need 2 pens - red and blue"

        User:
        "Create a laptop repair ticket"

        department = "IT Department"
        description = null

        IMPORTANT:

        A command to create a ticket/request is NOT itself a description.

        If removing the ticket-creation command leaves only:
        - a department name
        - a system name
        - a category/subcategory name
        - a request type

        then description = null.

        Example:

        "Create a SAP BASIS service request"

        After removing:
        "Create a" + "service request"

        only "SAP BASIS" remains.

        SAP BASIS identifies the system/subcategory but does not describe
        what the user needs.

        Therefore:
        description = null

        ==================================================
        LOCATION
        ==================================================

        Populate location only when the user explicitly provides a plant,
        office, site or location in the current message.

        Otherwise:
        location = null

        ==================================================
        PRIORITY
        ==================================================

        Allowed priorities:

        - Low
        - Medium
        - High
        - Critical

        Populate priority only when explicitly provided.

        Otherwise:
        priority = null

        ==================================================
        CHECK TICKET STATUS
        ==================================================

        When asking about one specific ticket:

        intent = "CHECK_TICKET_STATUS"

        Extract ticket_number when present.

        ticket_query must be one of:

        - STATUS
        - DETAILS
        - ASSIGNED_TO
        - REQUESTER
        - CREATED_DATE
        - UNKNOWN

        Examples:

        "What is the status of <TICKET_NUMBER>?"
        → ticket_query = "STATUS"

        "Who is assigned to <TICKET_NUMBER>?"
        → ticket_query = "ASSIGNED_TO"

        "Who raised <TICKET_NUMBER>?"
        → ticket_query = "REQUESTER"

        "When was <TICKET_NUMBER> created?"
        → ticket_query = "CREATED_DATE"

        For CHECK_TICKET_STATUS:
        department = null
        request_type = null
        category = null
        description = null
        location = null
        priority = null
        search_query = null
        search_scope = null

        ==================================================
        SEARCH TICKETS
        ==================================================

        When the user wants to find/list/search tickets:

        intent = "SEARCH_TICKETS"

        Extract the main search term into search_query.

        If the user refers to their own tickets:
        search_scope = "MY_TICKETS"

        Otherwise:
        search_scope = "ALL_TICKETS"

        Examples:

        "Find my laptop tickets"
        → search_query = "laptop"
        → search_scope = "MY_TICKETS"

        "Show tickets about network"
        → search_query = "network"
        → search_scope = "ALL_TICKETS"

        For SEARCH_TICKETS:
        department = null
        request_type = null
        ticket_number = null

        ==================================================
        CREATE TICKET SAFETY
        ==================================================

        For CREATE_TICKET:

        Never invent missing information.

        Never copy a description from an example.

        Never transform a vague request into a specific problem.

        If the user names only a system/item/request type, do not invent
        why they need it.

        Information not present in the current message must be null.

        Department classification is allowed from clear business meaning,
        but factual ticket details must come from the user's message.

        ==================================================
        FINAL
        ==================================================

        Return ONLY valid JSON.

        Do not add text before or after the JSON.

        Use null for unknown values.

        Never invent information.
        """
        # Add current ticket context when available.
        context_message = ""

        # Only reuse the previous ticket when the employee
        # explicitly refers back to that ticket.
        message_lower = user_message.lower()

        ticket_context_reference = bool(
            re.search(
                r"\b("
                r"this ticket|"
                r"that ticket|"
                r"my ticket|"
                r"the ticket|"
                r"its status|"
                r"it"
                r")\b",
                message_lower,
            )
        )

        if current_ticket_number and ticket_context_reference:
            
            context_message = f"""
        CURRENT TICKET CONTEXT:

        The user is currently discussing ticket:
        {current_ticket_number}

        If the user says:
        - it
        - this ticket
        - that ticket
        - my ticket

        and does not provide another ticket number, use:
        {current_ticket_number}

        Do not replace the current ticket number unless the user
        explicitly provides a different ticket number.

        IMPORTANT:

        Current ticket context must NEVER be used to populate:

        - department
        - request_type
        - category
        - description
        - location
        - priority

        for a new CREATE_TICKET request.

        CREATE_TICKET information must come only from the current
        user message.
        """

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]

        if context_message:
            messages.append(
                {
                    "role": "system",
                    "content": context_message,
                }
            )

        messages.append(
            {
                "role": "user",
                "content": user_message,
            }
        )

        response = self.llm.chat(
            messages,
            chat_id=chat_id
        )

        print("\nRAW LLM RESPONSE:")
        print(response)

        result = self._parse_json(response)

        # ---------------------------------------------------------
        # Ensure new fields always exist
        # ---------------------------------------------------------
        if "department" not in result:
            result["department"] = None

        # ---------------------------------------------------------
        # Validate department returned by the LLM.
        # Never allow invented department names into the workflow.
        # ---------------------------------------------------------

        allowed_departments = [
            "Branding",
            "Admin",
            "Safety",
            "Security",
            "Insurance",
            "Compliance & Risk",
            "HR Department",
            "Projects",
            "Finance",
            "IT Department",
            "Quality management",
            "Strategy",
        ]

        if result.get("department") not in allowed_departments:
            result["department"] = None

        # ---------------------------------------------------------
        # Request Type must ALWAYS be selected by the employee.
        # Never allow the initial LLM extraction to preselect it.
        # ---------------------------------------------------------

        if result.get("intent") == "CREATE_TICKET":

            # Request Type must always be selected by the employee.
            result["request_type"] = None
            # Location must always be explicitly selected by the employee.
            # A plant/site mentioned inside the problem description does
            # not necessarily represent the employee's ticket location.
            result["location"] = None

            # Preserve the employee's original requirement as the
            # ticket description instead of allowing the LLM to
            # shorten, rewrite or drop it.
            original_message = user_message.strip()

            if original_message:
                result["description"] = original_message

        elif "request_type" not in result:
            result["request_type"] = None

        # ---------------------------------------------------------
        # Deterministic protection for ticket collection queries
        # ---------------------------------------------------------
        # Questions about multiple tickets or ticket counts must
        # never inherit/invent one specific ticket number.

        message_lower = user_message.lower().strip()

        is_ticket_collection_query = (
            (
                "ticket" in message_lower
                or "tickets" in message_lower
            )
            and (
                "how many" in message_lower
                or "count" in message_lower
                or "show all" in message_lower
                or "show my" in message_lower
                or "list all" in message_lower
                or "list my" in message_lower
                or "find all" in message_lower
                or "find my" in message_lower
            )
        )

        if is_ticket_collection_query:
            result["intent"] = "SEARCH_TICKETS"
            result["ticket_number"] = None
            result["ticket_query"] = None

            result["ticket_count_only"] = (
                "how many" in message_lower
                or "count" in message_lower
            )

        # --------------------------------------------------
        # --------------------------------------------------
        # DETECT DEPARTMENT FOR TICKET SEARCH
        # Must run AFTER collection-query intent correction
        # --------------------------------------------------
        if result.get("intent") == "SEARCH_TICKETS":

            department_search_names = {
                "admin": "Admin",
                "branding": "Branding",
                "compliance & risk": "Compliance & Risk",
                "compliance and risk": "Compliance & Risk",
                "finance": "Finance",
                "hr department": "HR Department",
                "hr": "HR Department",
                "it department": "IT Department",
                "insurance": "Insurance",
                "projects": "Projects",
                "quality management": "Quality management",
                "safety": "Safety",
                "security": "Security",
                "strategy": "Strategy",
            }

            detected_department = None

            # First use explicit department words from the user's message.
            for phrase, department_name in department_search_names.items():
                if phrase in message_lower:
                    detected_department = department_name
                    break

            # If not found in the message, use a valid department
            # already identified by the LLM.
            if not detected_department:
                llm_department = result.get("department")

                if llm_department in department_search_names.values():
                    detected_department = llm_department

            result["search_department"] = detected_department

        # --------------------------------------------------
        # EXTRACT KEYWORD FOR DEPARTMENT TICKET SEARCH
        # --------------------------------------------------
        if (
            result.get("intent") == "SEARCH_TICKETS"
            and result.get("search_department")
        ):
            department_name = result.get("search_department")

            search_text = message_lower

            # Remove collection/count language.
            cleanup_phrases = [
                "how many",
                "count",
                "show all",
                "show my",
                "list all",
                "list my",
                "find all",
                "find my",
                "tickets",
                "ticket",
            ]

            # Remove department wording.
            department_phrases = {
                "Admin": ["admin"],
                "Branding": ["branding"],
                "Compliance & Risk": [
                    "compliance & risk",
                    "compliance and risk",
                ],
                "Finance": ["finance"],
                "HR Department": [
                    "hr department",
                    "hr",
                ],
                "IT Department": [
                    "it department",
                    "it",
                ],
                "Insurance": ["insurance"],
                "Projects": ["projects"],
                "Quality management": [
                    "quality management",
                ],
                "Safety": ["safety"],
                "Security": ["security"],
                "Strategy": ["strategy"],
            }

            cleanup_phrases.extend(
                department_phrases.get(department_name, [])
            )

            # Remove status words because they are handled separately.
            cleanup_phrases.extend([
                "open",
                "resolved",
                "closed",
                "cancelled",
            ])

            # Longest phrases first.
            cleanup_phrases.sort(
                key=len,
                reverse=True,
            )

            for phrase in cleanup_phrases:
                search_text = search_text.replace(
                    phrase,
                    " ",
                )

            search_text = " ".join(
                search_text.split()
            ).strip()

            filler_phrases = [
                "are there",
                "is there",
                "do we have",
            ]

            for phrase in filler_phrases:
                search_text = search_text.replace(
                    phrase,
                    " ",
                )

            # Remove punctuation left over from the user's question.
            search_text = re.sub(
                r"[^\w\s-]",
                " ",
                search_text,
            )

            # Normalize extra spaces.
            search_text = " ".join(
                search_text.split()
            ).strip()

            result["search_query"] = search_text or None

        # ---------------------------------------------------------
        # Deterministic ticket-query routing
        # ---------------------------------------------------------

        if result.get("intent") == "CHECK_TICKET_STATUS":

            message_lower = user_message.lower()

            if (
                "who raised" in message_lower
                or "who created" in message_lower
                or "who submitted" in message_lower
                or "raised by" in message_lower
                or "created by" in message_lower
                or "submitted by" in message_lower
            ):
                result["ticket_query"] = "REQUESTER"

            elif (
                "who is assigned" in message_lower
                or "who assigned" in message_lower
                or "who is handling" in message_lower
                or "who is working on" in message_lower
                or "assigned to" in message_lower
            ):
                result["ticket_query"] = "ASSIGNED_TO"

            elif (
                "when was" in message_lower
                and "created" in message_lower
            ) or (
                "when did" in message_lower
                and "raise" in message_lower
            ) or (
                "created date" in message_lower
            ):
                result["ticket_query"] = "CREATED_DATE"

            elif (
                "what is the status" in message_lower
                or "what's the status" in message_lower
                or "current status" in message_lower
                or "ticket status" in message_lower
                or "is my ticket open" in message_lower
                or "has my ticket been resolved" in message_lower
            ):
                result["ticket_query"] = "STATUS"

            elif (
                "show me the details" in message_lower
                or "ticket details" in message_lower
                or "details of the ticket" in message_lower
                or "tell me everything" in message_lower
            ):
                result["ticket_query"] = "DETAILS"

        # ---------------------------------------------------------
        # Deterministic validation of missing fields
        # ---------------------------------------------------------

        intent = result.get("intent")

        if intent == "CREATE_TICKET":

            required_fields = [
                "category",
                "description",
                "location",
                "priority",
            ]

            result["missing_fields"] = [
                field
                for field in required_fields
                if not result.get(field)
            ]

        elif intent == "CHECK_TICKET_STATUS":

            result["missing_fields"] = []

            if not result.get("ticket_number"):
                result["missing_fields"].append("ticket_number")

        elif intent == "SEARCH_TICKETS":

            result["missing_fields"] = []

            # A text search term is not required when the employee
            # is using a structured ticket filter.
            #
            # Example:
            # "Show my open tickets"
            # -> ticket_status_filter = "OPEN"
            # -> search_query can be None

            if (
                not result.get("search_query")
                and not result.get("ticket_status_filter")
            ):
                result["missing_fields"].append("search_query")

        else:

            result["missing_fields"] = []

        # ---------------------------------------------------------
        # Deterministic safety fallback for SEARCH_TICKETS
        # ---------------------------------------------------------

        if result.get("intent") == "SEARCH_TICKETS":

            # -----------------------------------------------------
            # Search scope
            # -----------------------------------------------------
            # Explicit self-reference in the user's message must
            # override the LLM. Example:
            #
            # "Show my tickets" -> MY_TICKETS
            # "Show my laptop tickets" -> MY_TICKETS
            #
            # This prevents a valid-but-wrong LLM value such as
            # ALL_TICKETS from exposing unrelated users' tickets.

            detected_scope = self._detect_search_scope(
                user_message
            )

            if detected_scope == "MY_TICKETS":
                result["search_scope"] = "MY_TICKETS"

            elif result.get("search_scope") not in [
                "MY_TICKETS",
                "ALL_TICKETS",
            ]:
                result["search_scope"] = detected_scope

            # -----------------------------------------------------
            # Search query
            # -----------------------------------------------------

            if not result.get("search_query"):
                result["search_query"] = self._detect_search_query(
                    user_message
                )

            # "all" is a scope instruction, not a search keyword.
            if result.get("search_scope") in ["ALL_TICKETS", "MY_TICKETS"]:
                search_query = str(
                    result.get("search_query") or ""
                ).strip().lower()

                if search_query in [
                    "all",
                    "my",
                    "ticket",
                    "tickets",
                    "my ticket",
                    "my tickets",
                    "all ticket",
                    "all tickets",
                ]:
                    result["search_query"] = None

            # -----------------------------------------------------
            # Ticket status filter
            # -----------------------------------------------------

            message_lower = user_message.lower().strip()
            message_words = message_lower.split()

            has_ticket_context = (
                "ticket" in message_lower
                or "tickets" in message_lower
            )

            # -----------------------------------------------------
            # Detect structured ticket status
            # -----------------------------------------------------

            if has_ticket_context:

                if "resolved" in message_words:
                    result["ticket_status_filter"] = "RESOLVED"

                elif "closed" in message_words:
                    result["ticket_status_filter"] = "CLOSED"

                elif (
                    "cancelled" in message_words
                    or "canceled" in message_words
                ):
                    result["ticket_status_filter"] = "CANCELLED"

                elif (
                    "open" in message_words
                    or "active" in message_words
                ):
                    result["ticket_status_filter"] = "OPEN"

                else:
                    result["ticket_status_filter"] = None

            else:
                result["ticket_status_filter"] = None

            # -----------------------------------------------------
            # Status words are filters, not semantic search terms
            # -----------------------------------------------------

            search_query = str(
                result.get("search_query") or ""
            ).strip().lower()

            # Status words belong to ticket_status_filter,
            # not to the semantic API search query.
            if result.get("ticket_status_filter"):

                status_words = [
                    "resolved",
                    "closed",
                    "cancelled",
                    "canceled",
                    "open",
                    "active",
                ]

                query_words = search_query.split()

                query_words = [
                    word
                    for word in query_words
                    if word not in status_words
                ]

                search_query = " ".join(query_words).strip()

                # If only generic ticket words remain, there is
                # no semantic keyword to search for.
                if search_query in [
                    "ticket",
                    "tickets",
                    "my ticket",
                    "my tickets",
                    "all",
                    "all ticket",
                    "all tickets",
                ]:
                    search_query = ""

                result["search_query"] = search_query

            # A search keyword is not required when a structured
            # status filter is present.
            if result.get("ticket_status_filter"):
                result["missing_fields"] = [
                    field
                    for field in result.get("missing_fields", [])
                    if field != "search_query"
                ]

        # ---------------------------------------------------------
        # Deterministic cleanup for non-create intents
        # ---------------------------------------------------------

        if result.get("intent") in [
            "CHECK_TICKET_STATUS",
            "SEARCH_TICKETS",
            "OTHER",
        ]:
            result["department"] = None
            result["request_type"] = None

        if "ticket_count_only" not in result:
            result["ticket_count_only"] = False

        if "search_department" not in result:
            result["search_department"] = None

        # ---------------------------------------------------------
        # Deterministic ticket-search department detection
        # ---------------------------------------------------------
        message_lower = user_message.lower().strip()

        # ---------------------------------------------------------
        # Remove department-only text from semantic search query
        # ---------------------------------------------------------
        if result.get("search_department") == "IT Department":
            search_query = str(
                result.get("search_query") or ""
            ).strip().lower()

            # Remove department wording from keyword searches.
            # Example:
            # "IT Department laptop tickets" -> "laptop"
            cleanup_phrases = [
                "it department",
                "it tickets",
                "it ticket",
            ]

            for phrase in cleanup_phrases:
                search_query = search_query.replace(phrase, " ")

            # Remove generic ticket words.
            words = search_query.split()

            words = [
                word
                for word in words
                if word not in ["ticket", "tickets"]
            ]

            search_query = " ".join(words).strip()

            result["search_query"] = search_query or None

        return result

    def classify_request_type(
        self,
        description,
        department,
        allowed_request_types,
    ):
        """
        Recommend the most appropriate request type from the
        request types actually available for the department.

        This is advisory only. The employee's explicit selection
        must never be silently overridden.
        """

        if not description:
            return None

        if not department:
            return None

        if not allowed_request_types:
            return None

        # If the department has only one possible request type,
        # there is no meaningful mismatch to detect.
        if len(allowed_request_types) <= 1:
            return None

        allowed_text = "\n".join(
            f"- {request_type}"
            for request_type in allowed_request_types
        )

        system_prompt = f"""
    You are a strict ticket request-type classifier for Darpan.

    Your task is to determine which request type BEST matches
    the employee's requirement.

    Department:
    {department}

    ALLOWED REQUEST TYPES:

    {allowed_text}

    You MUST choose ONLY from the allowed request types above.

    GENERAL MEANING:

    Incident Request:
    Use when the employee is reporting that something existing
    is broken, unavailable, failing, malfunctioning, interrupted,
    or not working as expected.

    Examples:
    - laptop is not starting
    - mouse stopped working
    - network is down
    - AC is not working
    - system is giving an error

    Service Request:
    Use when the employee is asking for something to be provided,
    issued, arranged, created, installed, enabled, booked,
    replaced as a normal requirement, or otherwise fulfilled.

    Examples:
    - I need a new mouse
    - I need pens
    - I need a business card
    - install software for me
    - provide access
    - book a conference room

    IMPORTANT:

    "I need a mouse" is normally a Service Request.

    "My mouse is not working" is normally an Incident Request.

    A request for a NEW item/service is different from reporting
    that an EXISTING item/service has failed.

    For other request types such as Change Management or
    Request For Information, use their normal business meaning
    only when those exact values are present in ALLOWED REQUEST TYPES.

    If the description is too ambiguous to confidently distinguish
    between the allowed request types, return null.

    Return ONLY valid JSON:

    {{
        "request_type": "<exact allowed request type or null>"
    }}

    RULES:

    1. Never invent a request type.

    2. The returned value must exactly match one value from
    ALLOWED REQUEST TYPES.

    3. Do not decide based only on a single keyword. Understand
    whether the employee is reporting a problem or requesting
    something to be provided.

    4. If uncertain, return null.

    5. Do not include explanations, markdown or additional text.

    Return JSON only.
    """

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": description,
            },
        ]

        response = self.llm.chat(messages)

        print("\nREQUEST TYPE CLASSIFIER RAW RESPONSE:")
        print(response)

        result = self._parse_json(response)

        recommended_request_type = result.get(
            "request_type"
        )

        # Never trust an LLM value without validating it.
        if (
            not recommended_request_type
            or recommended_request_type
            not in allowed_request_types
        ):
            return None

        return recommended_request_type

    def classify_category(
        self,
        description,
        department,
        request_type,
        allowed_categories,
    ):
        """
        Classify a ticket description into an allowed category/subcategory.

        The LLM is NOT allowed to invent values.
        It must choose only from allowed_categories.
        """

        if not description:
            return {
                "category": None,
                "subcategory": None,
            }

        if not department:
            return {
                "category": None,
                "subcategory": None,
            }

        if not request_type:
            return {
                "category": None,
                "subcategory": None,
            }

        if not allowed_categories:
            return {
                "category": None,
                "subcategory": None,
            }

        # -------------------------------------------------
        # Deterministic classification for clear business terms
        # -------------------------------------------------

        description_lower = description.lower()

        deterministic_rules = {
            "Admin": [
                (
                    ["ac", "air conditioner", "air conditioning"],
                    "Facility Management",
                    "AC Repair",
                ),
                (
                    ["electrical", "electricity", "power issue"],
                    "Facility Management",
                    "Electrical Issue",
                ),
                (
                    ["plumbing", "water leakage", "water leak"],
                    "Facility Management",
                    "Plumbing Issue",
                ),
            ],

            "Safety": [
                (
                    ["unsafe condition"],
                    "Incident Reporting & Management",
                    "Unsafe Condition Reporting",
                ),
                (
                    ["unsafe act"],
                    "Incident Reporting & Management",
                    "Unsafe Act Reporting",
                ),
                (
                    ["near miss"],
                    "Incident Reporting & Management",
                    "Near Miss Reporting",
                ),
                (
                    ["accident", "got injured", "was injured", "injury"],
                    "Incident Reporting & Management",
                    "Accident Reporting",
                ),
                (
                    ["ppe replacement", "replace my ppe", "replace ppe"],
                    "PPE Compliance",
                    "PPE Replacement Request",
                ),
                (
                    ["ppe", "safety helmet", "safety shoes"],
                    "PPE Compliance",
                    "PPE Issuance",
                ),
                (
                    ["plant audit"],
                    "Safety Audits & Inspections",
                    "Plant Audit Scheduling",
                ),
                (
                    ["office safety inspection"],
                    "Safety Audits & Inspections",
                    "Office Safety Inspection",
                ),
                (
                    ["safety induction"],
                    "Training & Awareness",
                    "Safety Induction Request",
                ),
                (
                    ["safety training"],
                    "Training & Awareness",
                    "Safety Training Scheduling",
                ),
            ],

            "Security": [
                (
                    [
                        "stole",
                        "stolen",
                        "theft",
                        "stealing",
                    ],
                    "Security Incident Management",
                    "Theft Reporting",
                ),
                (
                    [
                        "security breach",
                        "breach",
                        "unauthorized physical access",
                        "unauthorised physical access",
                        "intrusion",
                    ],
                    "Security Incident Management",
                    "Security Breach Reporting",
                ),
                (
                    [
                        "lost id card",
                        "lost my id card",
                        "id card lost",
                        "missing id card",
                        "lost identity card",
                    ],
                    "Security Incident Management",
                    "Lost ID Card Reporting",
                ),
            ],

            "Branding": [
                (
                    [
                        "board presentation",
                        "board presentations",
                        "board meeting",
                    ],
                    "Corporate Communication",
                    "Board Presentations",
                ),
                (
                    [
                        "exhibition stall",
                        "exhibition booth",
                        "stall branding",
                        "booth branding",
                    ],
                    "Events & Exhibitions",
                    "Stall/Booth Branding",
                ),
            ],
        }

        for keywords, category, subcategory in deterministic_rules.get(
            department,
            [],
        ):
            if any(
                keyword in description_lower
                for keyword in keywords
            ):
                # Still validate against the request-type-filtered
                # allowed catalog before accepting the rule.
                if (
                    category in allowed_categories
                    and subcategory
                    in allowed_categories.get(category, [])
                ):
                    return {
                        "category": category,
                        "subcategory": subcategory,
                    }

        # -------------------------------------------------
        # Build exact allowed Category -> Subcategory list
        # -------------------------------------------------

        allowed_lines = []

        for category, subcategories in allowed_categories.items():
            for subcategory in subcategories:
                allowed_lines.append(
                    f"- {category} -> {subcategory}"
                )

        allowed_text = "\n".join(allowed_lines)

        # -------------------------------------------------
        # LLM classification
        # -------------------------------------------------

        system_prompt = f"""
    You are a strict ticket category classifier for Darpan.

    Classify the employee's requirement using ONLY the allowed
    Category -> Subcategory combinations below.

    IMPORTANT CATEGORY RULES:

    - "Department" and "Category" are different fields.

    - NEVER return the department name as the category unless that exact
    value appears as a category key inside ALLOWED CATEGORIES.

    - The category MUST be copied EXACTLY from one of the category keys
    in ALLOWED CATEGORIES.

    - The subcategory MUST be copied EXACTLY from one of the subcategories
    belonging to that selected category.

    - Do not invent, rename, shorten, normalize, translate, expand,
    abbreviate, or paraphrase category or subcategory values.

    - Ignore category/subcategory names from general knowledge.

    - ALLOWED CATEGORIES is the only valid source for category and
    subcategory output values.

    VERY IMPORTANT EXACT-VALUE RULE:

    The employee's wording does NOT need to exactly match the catalog.
    You should understand the employee's meaning.

    However, after determining the correct meaning, your OUTPUT MUST use
    the complete exact value from ALLOWED CATEGORIES.

    For example:

    If ALLOWED CATEGORIES contains:

    "ECR (Engineering Change Request)"

    and the employee says:

    "engineering change request"

    you MUST return:

    "ECR (Engineering Change Request)"

    NEVER return:

    "Engineering Change Request"

    NEVER return:

    "ECR"

    Likewise, if ALLOWED CATEGORIES contains:

    "ECN (Engineering Change Notice)"

    and the employee says:

    "engineering change notice"

    you MUST return:

    "ECN (Engineering Change Notice)"

    This rule applies GENERICALLY to all categories and subcategories.

    For example, if an allowed value contains:
    - an abbreviation
    - text inside parentheses
    - punctuation
    - "&"
    - "/"
    - "-"
    - capitalization
    - prefixes or suffixes

    the complete value must be copied exactly as it appears in
    ALLOWED CATEGORIES.

    Do not remove any part of an allowed value.

    DEPARTMENT VS CATEGORY EXAMPLE:

    Department:
    Insurance

    Allowed Categories:
    {{
        "Claim Initiation": [
            "Employee insurance claim",
            "Asset insurance claim"
        ]
    }}

    Description:
    "I need to submit an employee insurance claim"

    Correct:
    {{
        "category": "Claim Initiation",
        "subcategory": "Employee insurance claim"
    }}

    Incorrect:
    {{
        "category": "Insurance",
        "subcategory": "Employee insurance claim"
    }}

    The incorrect answer is invalid because "Insurance" is the department
    and is not a category key in ALLOWED CATEGORIES.

    CURRENT REQUEST:

    Department:
    {department}

    Request Type selected by the employee:
    {request_type}

    ALLOWED CATEGORIES AND SUBCATEGORIES:

    {allowed_text}

    Return ONLY valid JSON in exactly this format:

    {{
        "category": null,
        "subcategory": null
    }}

    RULES:

    1. Select a category and subcategory ONLY from the allowed combinations.

    2. Category must be copied character-for-character from an allowed
    category value.

    3. Subcategory must be copied character-for-character from an allowed
    subcategory value.

    4. Never create, rename, shorten, translate, normalize, abbreviate,
    expand or invent a category or subcategory.

    5. Understand normal employee language and map its business meaning
    to the closest valid combination when the meaning is clear.

    6. The category and subcategory must belong to the SAME allowed
    combination.

    7. Do not return only part of an allowed category or subcategory.

    8. If the requirement does not clearly match an allowed combination,
    return:

    {{
        "category": null,
        "subcategory": null
    }}

    Examples of semantic understanding:

    An employee asking for pens, pencils or similar writing supplies
    can match a writing-instrument subcategory if such a combination
    exists in the allowed list.

    An employee reporting an AC problem can match an AC repair
    subcategory if such a combination exists in the allowed list.

    An employee saying "engineering change request" can match
    "ECR (Engineering Change Request)" if that exact subcategory
    exists in the allowed list.

    An employee saying "engineering change notice" can match
    "ECN (Engineering Change Notice)" if that exact subcategory
    exists in the allowed list.

    Do not use these examples unless the corresponding values actually
    exist in the allowed combinations supplied above.

    For Quality Management customer complaints:

    - A complaint about damage, loss, breakage, or an issue occurring
    during transportation, shipment, delivery, or transit can match
    "Transit" if that exact subcategory exists in the allowed list.

    - A complaint specifically related to packaging can match
    "Packaging" if that exact subcategory exists in the allowed list.

    - A complaint related to storage conditions or an issue occurring
    during storage can match "Storage" if that exact subcategory exists
    in the allowed list.

    - A complaint related to raw material can match "Raw Material" if
    that exact subcategory exists in the allowed list.

    These are semantic examples only. Use them only when those exact
    values exist in ALLOWED CATEGORIES.

    For Strategy requests:

    - If the employee is proposing automation, digitization, workflow
    automation, system automation, or converting a manual process into
    an automated/digital process, match "Automation Proposal" under
    "Digital Transformation" if that exact combination exists.

    - If the employee is proposing an idea whose primary purpose is cost
    reduction, expense reduction, material saving, energy saving,
    resource saving, or another explicit cost-saving initiative, match
    "Cost Saving Idea" under "Innovation Management" if that exact
    combination exists.

    IMPORTANT:

    Do not classify an automation proposal as "Cost Saving Idea" merely
    because automation could indirectly save money.

    Classify according to the PRIMARY PURPOSE explicitly expressed by
    the employee.

    Examples:

    "I have an idea to automate our manual invoice processing"
    → Digital Transformation
    → Automation Proposal

    "We should automate the manual approval workflow"
    → Digital Transformation
    → Automation Proposal

    "I have an idea to reduce electricity consumption and save energy cost"
    → Innovation Management
    → Cost Saving Idea

    "I found a way to reduce packaging material cost"
    → Innovation Management
    → Cost Saving Idea

    Use these examples only when the corresponding exact values exist
    in ALLOWED CATEGORIES.    

    OUTPUT FORMAT RULE:

    Your entire response MUST consist of one JSON object only.

    Do NOT include:
    - explanations
    - reasoning
    - introductory text
    - concluding text
    - markdown
    - code fences
    - questions such as "Is this correct?"

    The first character of your response must be {{
    The last character of your response must be }}

    Return ONLY:

    {{
        "category": "<exact allowed category or null>",
        "subcategory": "<exact allowed subcategory or null>"
    }}

    FINAL CHECK BEFORE RESPONDING:

    Before returning JSON, verify:

    - Is category copied exactly from ALLOWED CATEGORIES?
    - Is subcategory copied exactly from ALLOWED CATEGORIES?
    - Does the subcategory belong to that category?
    - Did you accidentally shorten or paraphrase either value?

    If any answer is invalid, correct it using the exact allowed value.

    Return ONLY JSON.
    """

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": description,
            },
        ]

        response = self.llm.chat(messages)

        print("\nCATEGORY CLASSIFIER RAW RESPONSE:")
        print(response)

        result = self._parse_json(response)

        category = result.get("category")
        subcategory = result.get("subcategory")

        # -------------------------------------------------
        # Deterministic validation
        # Never trust an LLM category without validation.
        # -------------------------------------------------

        if not category or not subcategory:
            return {
                "category": None,
                "subcategory": None,
            }

        if category not in allowed_categories:
            return {
                "category": None,
                "subcategory": None,
            }

        if subcategory not in allowed_categories.get(category, []):
            return {
                "category": None,
                "subcategory": None,
            }

        return {
            "category": category,
            "subcategory": subcategory,
        }

    def _detect_search_scope(self, user_message):
        """
        Deterministic fallback for search scope.

        This is intentionally simple and only handles clear
        self-reference. The LLM remains responsible for the
        primary interpretation.
        """

        text = user_message.lower().strip()

        my_phrases = [
            "my ",
            "my tickets",
            "i raised",
            "i created",
            "i submitted",
            "i have raised",
            "i have created",
            "tickets i raised",
            "tickets i created",
            "tickets assigned to me",
            "assigned to me",
        ]

        for phrase in my_phrases:
            if phrase in text:
                return "MY_TICKETS"

        return "ALL_TICKETS"

    def _detect_search_query(self, user_message):
        """
        Simple fallback for common ticket search keywords.
        """

        text = user_message.lower()

        keyword_map = [
            ("laptop", "laptop"),
            ("screen", "screen"),
            ("keyboard", "keyboard"),
            ("network", "network"),
            ("internet", "network"),
            ("wifi", "network"),
            ("wi-fi", "network"),
            ("lan", "network"),
            ("desktop", "desktop"),
            ("software", "software"),
        ]

        for phrase, query in keyword_map:
            if phrase in text:
                return query

        return None

    def _parse_json(self, response):
        """
        Parse JSON returned by the LLM.

        Handles:
        - Markdown code fences
        - Extra text before/after JSON
        - Common truncated JSON at the end of a response
        """

        if not response:
            raise ValueError("LLM returned an empty response.")

        text = response.strip()

        # ---------------------------------------------------------
        # 1. Remove markdown code fences
        # ---------------------------------------------------------
        if text.startswith("```"):
            lines = text.splitlines()

            # Remove first line: ```json / ```
            if lines:
                lines = lines[1:]

            # Remove final ```
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            text = "\n".join(lines).strip()

        # ---------------------------------------------------------
        # 2. Try normal JSON parsing first
        # ---------------------------------------------------------
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # ---------------------------------------------------------
        # 3. Extract JSON object if LLM added extra text
        # ---------------------------------------------------------
        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1 and end > start:
            candidate = text[start:end + 1]

            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        # ---------------------------------------------------------
        # 4. Try repairing a truncated JSON response
        # ---------------------------------------------------------
        repaired = text

        # The most common case we are seeing:
        #
        # "priority": "High
        #
        # Add the missing quote.
        #
        if repaired.count('"') % 2 != 0:
            repaired += '"'

        # If the JSON object itself is incomplete,
        # close it.
        if repaired.count("{") > repaired.count("}"):
            repaired += "}"

        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

        # ---------------------------------------------------------
        # 5. Last attempt: extract the JSON object and repair it
        # ---------------------------------------------------------
        start = repaired.find("{")

        if start != -1:
            candidate = repaired[start:].strip()

            if candidate.count("{") > candidate.count("}"):
                candidate += "}"

            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass

        # ---------------------------------------------------------
        # 6. Nothing worked
        # ---------------------------------------------------------
        raise ValueError(
            "LLM did not return valid JSON:\n"
            f"{response}"
        )