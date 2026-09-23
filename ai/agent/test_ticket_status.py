from ai.agent.workflow import AgentWorkflow

workflow = AgentWorkflow()

queries = [
    "What is the status of INCS-061?",
    "Show me details of INCS-061",
    "Who is assigned to INCS-061?",
    "Who raised INCS-061?",
    "When was INCS-061 created?",
]

for query in queries:
    print("\n" + "=" * 70)
    print("USER:", query)

    result = workflow.process_message(query)

    print("RESULT:")
    print(result)