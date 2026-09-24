from ai.agent.orchestrator import AgentOrchestrator


orchestrator = AgentOrchestrator()

queries = [
    "Find my laptop tickets",
    "Show my network tickets",
    "What laptop tickets have I raised?",
    "Show all laptop tickets",
    "Find tickets related to network",
    "Show tickets about keyboard problems",
]


for query in queries:
    print("\n" + "=" * 70)
    print("USER:", query)

    result = orchestrator.understand_request(query)

    print("INTENT:", result.get("intent"))
    print("SEARCH QUERY:", result.get("search_query"))
    print("SEARCH SCOPE:", result.get("search_scope"))