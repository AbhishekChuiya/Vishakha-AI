import json
import re

from ai.llm.client import LocalLLM


class AgentOrchestrator:

    def __init__(self):
        self.llm = LocalLLM()

    def understand_request(self, user_message, current_ticket_number=None):

        system_prompt = """
You are a JSON information extraction engine for a company employee assistant.

Read the user's message carefully.

Return ONLY valid JSON.
Do not explain anything.
Do not use markdown.
Do not invent information.

The JSON MUST have exactly these fields:

{
    "intent": "...",
    "category": "...",
    "description": "...",
    "location": "...",
    "ticket_number": "...",
    "ticket_query": "...",
    "search_query": "...",
    "search_scope": "...",
    "priority": "...",
    "missing_fields": []
}


==================================================
ALLOWED INTENTS
==================================================

The allowed intent values are:

- CREATE_TICKET
- CHECK_TICKET_STATUS
- SEARCH_TICKETS
- OTHER


==================================================
ALLOWED CATEGORIES
==================================================

The allowed category values are:

- Laptop Repair
- Desktop Repair
- Network Issue
- Software Issue
- Other


==================================================
ALLOWED PRIORITIES
==================================================

The allowed priority values are:

- Low
- Medium
- High
- Critical


==================================================
TICKET QUERY VALUES
==================================================

For CHECK_TICKET_STATUS, ticket_query must be one of:

- STATUS
- DETAILS
- ASSIGNED_TO
- REQUESTER
- CREATED_DATE
- UNKNOWN


==================================================
SEARCH SCOPE VALUES
==================================================

For SEARCH_TICKETS, search_scope MUST be exactly one of:

- MY_TICKETS
- ALL_TICKETS

Never return null for search_scope when intent is SEARCH_TICKETS.


==================================================
CREATE_TICKET RULES
==================================================

1. If the user wants to report, create, raise, log, or open an
   IT/service issue, use:

   intent = "CREATE_TICKET"

2. If the user mentions laptop, laptop problem, laptop repair,
   laptop issue, or similar:

   category = "Laptop Repair"

3. If the user mentions desktop or computer desktop problem:

   category = "Desktop Repair"

4. If the user mentions network, internet, Wi-Fi, LAN,
   connectivity, network connection, or similar:

   category = "Network Issue"

5. If the user mentions software, application, or application error:

   category = "Software Issue"
6. DESCRIPTION RULE:

For CREATE_TICKET, description must ONLY contain information
explicitly present in the CURRENT user message.

NEVER copy, reuse, or infer a description from:
- previous user messages
- previous tickets
- conversation history
- examples
- current ticket context

If the current user message does not describe the problem,
description MUST be null.

Examples:

User:
"Create a laptop repair ticket for Ahmedabad Plant."

description = null

User:
"My laptop screen is not working. Create a ticket."

description = "My laptop screen is not working"

User:
"My laptop keyboard is not working."

description = "My laptop keyboard is not working"


7. If the user explicitly mentions a plant, office, location,
city, or site in the CURRENT message, put that information
into location.

8. If the user explicitly says low, medium, high, or critical
priority in the CURRENT message, put that value into priority.

9. NEVER copy information from a previous user message into the
current CREATE_TICKET request.

10. NEVER invent missing information.

11. If information is not provided in the CURRENT user message,
use null.


12. MISSING FIELD RULES:    

For CREATE_TICKET:
Required fields are ONLY:
- category
- description
- location
- priority

For CREATE_TICKET, missing_fields must contain ONLY the required
fields whose values are null.

Do NOT include these fields in missing_fields for CREATE_TICKET:
- ticket_number
- ticket_query
- search_query
- search_scope

For CHECK_TICKET_STATUS:
Required field:
- ticket_number

For SEARCH_TICKETS:
Required field:
- search_query

search_scope is NOT a missing field.
search_scope must be MY_TICKETS or ALL_TICKETS.

For OTHER:
missing_fields must be [].

13. For CREATE_TICKET:

ticket_number = null
ticket_query = null
search_query = null
search_scope = null

==================================================
CHECK_TICKET_STATUS RULES
==================================================

14. If the user asks about ticket status, ticket progress,
    existing ticket, incident status, or asks to check a ticket:

    intent = "CHECK_TICKET_STATUS"

15. If the user provides a ticket number such as INCS-061,
    extract it into ticket_number.

16. Preserve the ticket number exactly as provided,
    except normalizing obvious lowercase/uppercase differences.

17. If no ticket number is provided:

    ticket_number = null

18. Do not create a ticket for a status request.

19. Determine ticket_query as follows:

    If the user asks:
    "What is the status?"
    "What is the current status?"
    "Is my ticket open?"
    "Has my ticket been resolved?"

    ticket_query = "STATUS"

    If the user asks:
    "Show me the details"
    "What are the ticket details?"
    "Tell me everything about the ticket"

    ticket_query = "DETAILS"

    If the user asks:
    "Who is assigned to it?"
    "Who is handling the ticket?"
    "Who is working on this ticket?"

    ticket_query = "ASSIGNED_TO"

    If the user asks:
    "Who raised it?"
    "Who created the ticket?"
    "Who submitted the ticket?"

    ticket_query = "REQUESTER"

    If the user asks:
    "When was it created?"
    "When did I raise this ticket?"
    "What date was the ticket created?"

    ticket_query = "CREATED_DATE"

    If none of the above can be determined:

    ticket_query = "UNKNOWN"

20. For CHECK_TICKET_STATUS:

    category = null
    description = null
    location = null
    priority = null
    search_query = null
    search_scope = null


==================================================
SEARCH_TICKETS RULES
==================================================

21. Use SEARCH_TICKETS when the user wants to find, search,
    show, list, or locate tickets based on a keyword, issue,
    category, or description.

22. If the user provides a specific ticket number such as INCS-061
    and asks about that specific ticket, use CHECK_TICKET_STATUS,
    NOT SEARCH_TICKETS.

23. For SEARCH_TICKETS, extract the main keyword or phrase
    into search_query.

Examples:

"Find my laptop tickets"
→ search_query = "laptop"

"Show tickets related to network"
→ search_query = "network"

"Find my screen issue ticket"
→ search_query = "screen"

"Show tickets about keyboard problems"
→ search_query = "keyboard"

24. SEARCH SCOPE:

Use:

search_scope = "MY_TICKETS"

when the user clearly refers to their own tickets.

Self-reference includes:

- my
- I raised
- I created
- I submitted
- I have raised
- I have created
- tickets I raised
- tickets I created
- tickets assigned to me

Examples:

"Find my laptop tickets"

→ intent = "SEARCH_TICKETS"
→ search_query = "laptop"
→ search_scope = "MY_TICKETS"

"Show my network tickets"

→ intent = "SEARCH_TICKETS"
→ search_query = "network"
→ search_scope = "MY_TICKETS"

"What laptop tickets have I raised?"

→ intent = "SEARCH_TICKETS"
→ search_query = "laptop"
→ search_scope = "MY_TICKETS"

"Show tickets I created about keyboard"

→ intent = "SEARCH_TICKETS"
→ search_query = "keyboard"
→ search_scope = "MY_TICKETS"


Use:

search_scope = "ALL_TICKETS"

when the user does NOT refer to their own tickets.

Examples:

"Show all laptop tickets"

→ intent = "SEARCH_TICKETS"
→ search_query = "laptop"
→ search_scope = "ALL_TICKETS"

"Find tickets related to network"

→ intent = "SEARCH_TICKETS"
→ search_query = "network"
→ search_scope = "ALL_TICKETS"

"Show tickets about keyboard problems"

→ intent = "SEARCH_TICKETS"
→ search_query = "keyboard"
→ search_scope = "ALL_TICKETS"

25. IMPORTANT:

For EVERY SEARCH_TICKETS request:

search_scope MUST be either:

"MY_TICKETS"

or:

"ALL_TICKETS"

NEVER return:

null

for search_scope when intent is SEARCH_TICKETS.

26. For SEARCH_TICKETS:

ticket_number = null
ticket_query = "UNKNOWN"
location = null
priority = null

category may be determined if obvious.

description may contain the issue description if useful.

27. If no useful search keyword can be identified:

search_query = null

But search_scope must still be determined as:

"MY_TICKETS"

or:

"ALL_TICKETS"


==================================================
OTHER RULES
==================================================

28. Greetings, general questions, or requests unrelated to
    ticketing:

    intent = "OTHER"

29. For OTHER:

    category = null
    description = null
    location = null
    priority = null
    ticket_number = null
    ticket_query = "UNKNOWN"
    search_query = null
    search_scope = null
    missing_fields = []


==================================================
IMPORTANT EXAMPLES
==================================================

Example 1:

User:
Create a laptop repair ticket

JSON:
{
    "intent": "CREATE_TICKET",
    "category": "Laptop Repair",
    "description": null,
    "location": null,
    "ticket_number": null,
    "ticket_query": null,
    "search_query": null,
    "search_scope": null,
    "priority": null,
    "missing_fields": [
        "description",
        "location",
        "priority"
    ]
}


Example 2:

User:
Create a laptop repair ticket for Ahmedabad Plant.

JSON:
{
    "intent": "CREATE_TICKET",
    "category": "Laptop Repair",
    "description": null,
    "location": "Ahmedabad Plant",
    "ticket_number": null,
    "ticket_query": null,
    "search_query": null,
    "search_scope": null,
    "priority": null,
    "missing_fields": [
        "description",
        "priority"
    ]
}

Example 3:

User:
Report a network issue

JSON:
{
    "intent": "CREATE_TICKET",
    "category": "Network Issue",
    "description": null,
    "location": null,
    "ticket_number": null,
    "ticket_query": null,
    "search_query": null,
    "search_scope": null,
    "priority": null,
    "missing_fields": [
        "description",
        "location",
        "priority"
    ]
}


Example 4:

User:
My laptop screen is not working at Ahmedabad plant.
Priority should be high.

JSON:
{
    "intent": "CREATE_TICKET",
    "category": "Laptop Repair",
    "description": "My laptop screen is not working",
    "location": "Ahmedabad plant",
    "ticket_number": null,
    "ticket_query": null,
    "search_query": null,
    "search_scope": null,
    "priority": "High",
    "missing_fields": []
}


Example 5:

User:
Check my ticket status

JSON:
{
    "intent": "CHECK_TICKET_STATUS",
    "category": null,
    "description": null,
    "location": null,
    "ticket_number": null,
    "ticket_query": "STATUS",
    "search_query": null,
    "search_scope": null,
    "priority": null,
    "missing_fields": []
}


Example 6:

User:
What is the status of INCS-061?

JSON:
{
    "intent": "CHECK_TICKET_STATUS",
    "category": null,
    "description": null,
    "location": null,
    "ticket_number": "INCS-061",
    "ticket_query": "STATUS",
    "search_query": null,
    "search_scope": null,
    "priority": null,
    "missing_fields": []
}


Example 7:

User:
Who is assigned to it?

If the current ticket is INCS-061:

JSON:
{
    "intent": "CHECK_TICKET_STATUS",
    "category": null,
    "description": null,
    "location": null,
    "ticket_number": "INCS-061",
    "ticket_query": "ASSIGNED_TO",
    "search_query": null,
    "search_scope": null,
    "priority": null,
    "missing_fields": []
}


Example 8:

User:
Find my laptop tickets

JSON:
{
    "intent": "SEARCH_TICKETS",
    "category": "Laptop Repair",
    "description": null,
    "location": null,
    "ticket_number": null,
    "ticket_query": "UNKNOWN",
    "search_query": "laptop",
    "search_scope": "MY_TICKETS",
    "priority": null,
    "missing_fields": []
}


Example 9:

User:
Show my network tickets

JSON:
{
    "intent": "SEARCH_TICKETS",
    "category": "Network Issue",
    "description": null,
    "location": null,
    "ticket_number": null,
    "ticket_query": "UNKNOWN",
    "search_query": "network",
    "search_scope": "MY_TICKETS",
    "priority": null,
    "missing_fields": []
}


Example 10:

User:
What laptop tickets have I raised?

JSON:
{
    "intent": "SEARCH_TICKETS",
    "category": "Laptop Repair",
    "description": null,
    "location": null,
    "ticket_number": null,
    "ticket_query": "UNKNOWN",
    "search_query": "laptop",
    "search_scope": "MY_TICKETS",
    "priority": null,
    "missing_fields": []
}


Example 11:

User:
Show all laptop tickets

JSON:
{
    "intent": "SEARCH_TICKETS",
    "category": "Laptop Repair",
    "description": null,
    "location": null,
    "ticket_number": null,
    "ticket_query": "UNKNOWN",
    "search_query": "laptop",
    "search_scope": "ALL_TICKETS",
    "priority": null,
    "missing_fields": []
}


Example 12:

User:
Find tickets related to network

JSON:
{
    "intent": "SEARCH_TICKETS",
    "category": "Network Issue",
    "description": null,
    "location": null,
    "ticket_number": null,
    "ticket_query": "UNKNOWN",
    "search_query": "network",
    "search_scope": "ALL_TICKETS",
    "priority": null,
    "missing_fields": []
}


Example 13:

User:
Show tickets about keyboard problems

JSON:
{
    "intent": "SEARCH_TICKETS",
    "category": "Laptop Repair",
    "description": "keyboard problems",
    "location": null,
    "ticket_number": null,
    "ticket_query": "UNKNOWN",
    "search_query": "keyboard",
    "search_scope": "ALL_TICKETS",
    "priority": null,
    "missing_fields": []
}


Example 14:

User:
Hello

JSON:
{
    "intent": "OTHER",
    "category": null,
    "description": null,
    "location": null,
    "ticket_number": null,
    "ticket_query": "UNKNOWN",
    "search_query": null,
    "search_scope": null,
    "priority": null,
    "missing_fields": []
}


==================================================
FINAL VALIDATION
==================================================

Before returning the JSON, verify:

1. intent is one of the allowed intent values.

2. If intent = SEARCH_TICKETS:
   - search_query is present when a keyword exists.
   - search_scope is ALWAYS "MY_TICKETS" or "ALL_TICKETS".
   - search_scope is NEVER null.

3. If intent = CHECK_TICKET_STATUS:
   - ticket_query is one of the allowed ticket query values.

4. If intent = CREATE_TICKET:
   - missing_fields contains every missing required field.

5. Do not invent information.

6. Return ONLY JSON.
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

        return result

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

        response = response.strip()

        # Remove markdown code fences
        response = re.sub(
            r"```json",
            "",
            response,
            flags=re.IGNORECASE
        )

        response = response.replace("```", "").strip()

        # Try direct JSON parsing
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON object from surrounding text
        match = re.search(
            r"\{.*\}",
            response,
            re.DOTALL
        )

        if match:
            return json.loads(match.group(0))

        raise ValueError(
            f"LLM did not return valid JSON:\n{response}"
        )