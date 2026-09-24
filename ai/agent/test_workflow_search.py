from ai.agent.workflow import AgentWorkflow


workflow = AgentWorkflow()

queries = [
    "Find my laptop tickets",
    "Show tickets related to network",
    "Find my screen issue ticket",
    "Show tickets about keyboard problems",
]


for query in queries:
    print("\n" + "=" * 70)
    print("USER:", query)

    result = workflow.process_message(query)

    print("TYPE:", result.get("type"))
    print("MESSAGE:", result.get("message"))

    tickets = result.get("tickets", [])

    print("TICKETS RETURNED:", len(tickets))

    for ticket in tickets[:5]:
        print(
            ticket.get("ticket_number"),
            "|",
            ticket.get("title"),
            "|",
            ticket.get("status"),
            "|",
            ticket.get("priority"),
        )