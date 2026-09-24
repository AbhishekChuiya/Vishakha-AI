from ai.agent.orchestrator import AgentOrchestrator


orchestrator = AgentOrchestrator()


queries = [
    "My laptop screen is not working. Create a high priority ticket for Ahmedabad Plant.",
    "My laptop screen is not working. Create a ticket.",
    "Create a laptop repair ticket for Ahmedabad Plant.",
    "My laptop keyboard is not working. Create a high priority ticket.",
]


for query in queries:
    print("=" * 80)
    print("USER:")
    print(query)
    print()

    result = orchestrator.understand_request(query)

    print("INTENT:", result.get("intent"))
    print("CATEGORY:", result.get("category"))
    print("DESCRIPTION:", result.get("description"))
    print("LOCATION:", result.get("location"))
    print("PRIORITY:", result.get("priority"))
    print("MISSING FIELDS:", result.get("missing_fields"))
    print()