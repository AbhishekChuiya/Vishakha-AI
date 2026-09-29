import json
import re

from ai.llm.client import LocalLLM


class AgentOrchestrator:

    def __init__(self):
        self.llm = LocalLLM()

    def understand_request(self, user_message, current_ticket_number=None):

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

        --------------------------------------------------
        CHECK_TICKET_STATUS
        --------------------------------------------------

        Use CHECK_TICKET_STATUS only when the employee is asking about
        one specific EXISTING ticket.

        Examples:

        "What is the status of INC-00029?"
        → CHECK_TICKET_STATUS

        "Who is assigned to SRQAD-083?"
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

        "What is the status of INCIT-00503?"
        → ticket_query = "STATUS"

        "Who is assigned to INCIT-00503?"
        → ticket_query = "ASSIGNED_TO"

        "Who raised INCIT-00503?"
        → ticket_query = "REQUESTER"

        "When was INCIT-00503 created?"
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

        if current_ticket_number:
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

        response = self.llm.chat(messages)

        print("\nRAW LLM RESPONSE:")
        print(response)

        result = self._parse_json(response)

        # ---------------------------------------------------------
        # Ensure new fields always exist
        # ---------------------------------------------------------
        if "department" not in result:
            result["department"] = None

        # ---------------------------------------------------------
        # Request Type must ALWAYS be selected by the employee.
        # Never allow the initial LLM extraction to preselect it.
        # ---------------------------------------------------------

        if result.get("intent") == "CREATE_TICKET":

            # Request Type must always be selected by the employee.
            result["request_type"] = None

            # Preserve the employee's original requirement as the
            # ticket description instead of allowing the LLM to
            # shorten, rewrite or drop it.
            original_message = user_message.strip()

            if original_message:
                result["description"] = original_message

        elif "request_type" not in result:
            result["request_type"] = None

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

            if not result.get("search_query"):
                result["missing_fields"].append("search_query")

        else:

            result["missing_fields"] = []

        # ---------------------------------------------------------
        # Deterministic safety fallback for SEARCH_TICKETS
        # ---------------------------------------------------------

        if result.get("intent") == "SEARCH_TICKETS":

            if result.get("search_scope") not in [
                "MY_TICKETS",
                "ALL_TICKETS",
            ]:
                result["search_scope"] = self._detect_search_scope(
                    user_message
                )

            if not result.get("search_query"):
                result["search_query"] = self._detect_search_query(
                    user_message
                )

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

        return result

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
                ["board presentation", "board presentations", "board meeting"],
                "Corporate Communication",
                "Board Presentations",
            ),
            (
                ["exhibition stall", "exhibition booth", "stall branding", "booth branding"],
                "Events & Exhibitions",
                "Stall/Booth Branding",
            ),
        ],
        }

        for keywords, category, subcategory in deterministic_rules.get(
            department,
            []
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

        allowed_lines = []

        for category, subcategories in allowed_categories.items():
            for subcategory in subcategories:
                allowed_lines.append(
                    f"- {category} -> {subcategory}"
                )

        allowed_text = "\n".join(allowed_lines)

        system_prompt = f"""
You are a strict ticket category classifier for Darpan.

Classify the employee's requirement using ONLY the allowed
Category -> Subcategory combinations below.

Department:
{department}

Request Type selected by the employee:
{request_type}

Allowed combinations:

{allowed_text}

Return ONLY valid JSON in exactly this format:

{{
    "category": null,
    "subcategory": null
}}

RULES:

1. Select a category and subcategory ONLY from the allowed combinations.

2. Never create, rename, shorten, translate or invent a category
   or subcategory.

3. Understand normal employee language and map its business meaning
   to the closest valid combination when the meaning is clear.

4. The category and subcategory must belong to the SAME allowed
   combination.

5. If the requirement does not clearly match an allowed combination,
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

Do not use these examples unless the corresponding values actually
exist in the allowed combinations supplied above.

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