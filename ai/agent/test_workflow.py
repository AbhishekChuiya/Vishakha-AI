from ai.agent.workflow import AgentWorkflow


workflow = AgentWorkflow()


print("\nUSER:")
print("Create a laptop repair ticket")


response = workflow.process_message(
    "Create a laptop repair ticket"
)


print("\nAI:")
print(response)


print("\nUSER:")
print("Screen not working")


response = workflow.handle_option(
    "Screen not working"
)


print("\nAI:")
print(response)


print("\nUSER:")
print("Ahmedabad Plant")


response = workflow.handle_option(
    "Ahmedabad Plant"
)


print("\nAI:")
print(response)


print("\nUSER:")
print("High")


response = workflow.handle_option(
    "High"
)


print("\nAI:")
print(response)