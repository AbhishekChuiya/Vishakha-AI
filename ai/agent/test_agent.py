from ai.agent.orchestrator import AgentOrchestrator


agent = AgentOrchestrator()


tests = [
    # "Create a laptop repair ticket",

    # "Create a laptop repair ticket. My laptop screen is not working. I am at the Ahmedabad plant. Priority should be high.",

    # "Report a network issue",

    # "Check my ticket status",

    # "Hello",
    
    # "What is the status of INCS-061?",

    "Create a ticket for my laptop",
    "Create an incident request for my laptop",
    "I want a service request for SAP",
    "I want to report a safety incident",
    "I need a branding change",
]


for request in tests:

    print("\n" + "=" * 70)
    print("USER REQUEST:")
    print(request)
    print("=" * 70)

    result = agent.understand_request(request)

    print("\nAGENT RESULT:")
    print(result)