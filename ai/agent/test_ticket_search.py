from ai.agent.orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator()

tests = [
    "Find my laptop tickets",
    "Show tickets related to network",
    "Find my screen issue ticket",
    "Show tickets about keyboard problems",
    "What is the status of INCS-061?",
]

for message in tests:
    print("\n" + "=" * 70)
    print("USER:", message)

    result = orchestrator.understand_request(message)

    print("RESULT:")
    print(result)