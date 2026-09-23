from ai.agent.orchestrator import AgentOrchestrator

agent = AgentOrchestrator()

queries = [
    "What is the status of INCS-061?",
    "Show me details of INCS-061",
    "Who is assigned to INCS-061?",
    "Who raised INCS-061?",
    "When was INCS-061 created?",
]

for query in queries:
    print("\n" + "=" * 60)
    print("USER:", query)

    result = agent.understand_request(query)

    print("RESULT:")
    print(result)