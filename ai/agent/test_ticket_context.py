from ai.agent.workflow import AgentWorkflow


workflow = AgentWorkflow()

print("\n" + "=" * 70)
print("USER: What is the status of INCS-061?")

result = workflow.process_message(
    "What is the status of INCS-061?"
)

print("RESULT:")
print(result)


print("\n" + "=" * 70)
print("USER: Who is assigned to it?")

result = workflow.process_message(
    "Who is assigned to it?"
)

print("RESULT:")
print(result)


print("\n" + "=" * 70)
print("USER: Who raised it?")

result = workflow.process_message(
    "Who raised it?"
)

print("RESULT:")
print(result)