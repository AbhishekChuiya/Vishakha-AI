import json
import re

from ai.llm.client import LocalLLM


class AgentOrchestrator:

    def __init__(self):
        self.llm = LocalLLM()

    def understand_request(self, user_message):

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
    "priority": "...",
    "missing_fields": []
}

Allowed intent values:

- CREATE_TICKET
- CHECK_TICKET_STATUS
- OTHER

Allowed category values:

- Laptop Repair
- Desktop Repair
- Network Issue
- Software Issue
- Other

Allowed priority values:

- Low
- Medium
- High
- Critical

RULES FOR CREATE_TICKET:

1. If the user wants to report, create, raise, log, or open an IT/service
   issue, use intent = "CREATE_TICKET".

2. If the user mentions laptop, laptop problem, laptop repair,
   laptop issue, or similar:
   category = "Laptop Repair".

3. If the user mentions desktop or computer desktop problem:
   category = "Desktop Repair".

4. If the user mentions network, internet, Wi-Fi, LAN, connectivity,
   network connection, or similar:
   category = "Network Issue".

5. If the user mentions software/application/application error:
   category = "Software Issue".

6. If the user explicitly describes the problem,
   put that information into description.

7. If the user explicitly mentions a plant, office, location,
   city, or site:
   put that information into location.

8. If the user explicitly says low, medium, high, or critical priority:
   put that value into priority.

9. NEVER invent missing information.

10. If information is not provided, use null.

11. For CREATE_TICKET, missing_fields must contain the fields whose
    values are null.

RULES FOR CHECK_TICKET_STATUS:

12. If the user asks about ticket status, ticket progress,
    existing ticket, incident status, or asks to check their ticket:
    intent = "CHECK_TICKET_STATUS".

13. If the user provides a ticket number such as INCS-061,
    extract it into ticket_number.

14. Preserve the ticket number exactly as provided,
    except normalizing obvious lowercase/uppercase differences.

15. If no ticket number is provided, ticket_number = null.

16. Do not create a ticket for a status request.


RULES FOR OTHER:

17. Greetings, general questions, or requests unrelated to ticketing:
    intent = "OTHER".

    
TICKET QUERY RULES:

18. ticket_query MUST ALWAYS be one of:
    - STATUS
    - DETAILS
    - ASSIGNED_TO
    - REQUESTER
    - CREATED_DATE
    - UNKNOWN

19. If the user asks:
    "What is the status of..."
    "What is the state of..."
    "What is the progress of..."
    "Check the status of..."
    "Check my ticket..."
    "What is happening with..."
    ticket_query = "STATUS"

20. If the user asks:
    "Show me details of..."
    "Show ticket details..."
    "Show information about..."
    "Give me details..."
    "Tell me about this ticket..."
    ticket_query = "DETAILS"

21. If the user asks:
    "Who is assigned to..."
    "Who is handling..."
    "Who is working on..."
    "Who has this ticket..."
    ticket_query = "ASSIGNED_TO"

22. If the user asks:
    "Who raised..."
    "Who created..."
    "Who requested..."
    "Who reported..."
    ticket_query = "REQUESTER"

23. If the user asks:
    "When was ... created?"
    "When did ... get created?"
    "What is the creation date..."
    ticket_query = "CREATED_DATE"

24. If the user provides a ticket number but the requested information
    cannot be determined:
    ticket_query = "UNKNOWN"

25. If the user provides a ticket number such as INCS-061,
    extract it into ticket_number.

26. For CHECK_TICKET_STATUS, ticket_query must never be null.

IMPORTANT EXAMPLE:

User:
Create a laptop repair ticket

JSON:
{
    "intent": "CREATE_TICKET",
    "category": "Laptop Repair",
    "ticket_number": null,
    "description": null,
    "location": null,
    "priority": null,
    "missing_fields": ["description", "location", "priority"]
}

IMPORTANT EXAMPLE:

User:
Report a network issue

JSON:
{
    "intent": "CREATE_TICKET",
    "category": "Network Issue",
    "description": null,
    "location": null,
    "priority": null,
    "ticket_number": null,
    "missing_fields": ["description", "location", "priority"]
}

IMPORTANT EXAMPLE:

User:
My laptop screen is not working at Ahmedabad plant.
Priority should be high.

JSON:
{
    "intent": "CREATE_TICKET",
    "category": "Laptop Repair",
    "description": "My laptop screen is not working",
    "location": "Ahmedabad plant",
    "priority": "High",
    "ticket_number": null,
    "missing_fields": []
}

IMPORTANT EXAMPLE:

User:
Check my ticket status

JSON:
{
    "intent": "CHECK_TICKET_STATUS",
    "category": null,
    "description": null,
    "location": null,
    "ticket_number": null
    "priority": null,
    "missing_fields": []
}

IMPORTANT EXAMPLE:

User:
Hello

JSON:
{
    "intent": "OTHER",
    "category": null,
    "description": null,
    "location": null,
    "ticket_number": null,
    "priority": null,
    "missing_fields": []
}

IMPORTANT EXAMPLE:

User:
What is the status of INCS-061?

JSON:
{
    "intent": "CHECK_TICKET_STATUS",
    "category": null,
    "description": null,
    "location": null,
    "priority": null,
    "ticket_number": "INCS-061",
    "missing_fields": []
}

EXAMPLES:

User: What is the status of INCS-061?
JSON:
{
    "intent": "CHECK_TICKET_STATUS",
    "category": null,
    "description": null,
    "location": null,
    "ticket_number": "INCS-061",
    "ticket_query": "STATUS",
    "priority": null,
    "missing_fields": []
}

User: Show me details of INCS-061
JSON:
{
    "intent": "CHECK_TICKET_STATUS",
    "category": null,
    "description": null,
    "location": null,
    "ticket_number": "INCS-061",
    "ticket_query": "DETAILS",
    "priority": null,
    "missing_fields": []
}

User: Who is assigned to INCS-061?
JSON:
{
    "intent": "CHECK_TICKET_STATUS",
    "category": null,
    "description": null,
    "location": null,
    "ticket_number": "INCS-061",
    "ticket_query": "ASSIGNED_TO",
    "priority": null,
    "missing_fields": []
}

User: Who raised INCS-061?
JSON:
{
    "intent": "CHECK_TICKET_STATUS",
    "category": null,
    "description": null,
    "location": null,
    "ticket_number": "INCS-061",
    "ticket_query": "REQUESTER",
    "priority": null,
    "missing_fields": []
}

User: When was INCS-061 created?
JSON:
{
    "intent": "CHECK_TICKET_STATUS",
    "category": null,
    "description": null,
    "location": null,
    "ticket_number": "INCS-061",
    "ticket_query": "CREATED_DATE",
    "priority": null,
    "missing_fields": []
}

Now analyze the user's message.
"""

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]

        response = self.llm.chat(messages)

        print("\nRAW LLM RESPONSE:")
        print(response)

        return self._parse_json(response)

    def _parse_json(self, response):

        response = response.strip()

        # Remove markdown code fences
        response = re.sub(r"```json", "", response, flags=re.IGNORECASE)
        response = response.replace("```", "").strip()

        # Try direct JSON parsing
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON object from surrounding text
        match = re.search(r"\{.*\}", response, re.DOTALL)

        if match:
            return json.loads(match.group(0))

        raise ValueError(
            f"LLM did not return valid JSON:\n{response}"
        )