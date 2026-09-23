from ai.agent.conversation import ConversationState


state = ConversationState()


print("\nINITIAL STATE")
print(state.get_summary())


state.category = "Laptop Repair"

state.description = "My laptop screen is not working"

state.location = "Ahmedabad Plant"

state.priority = "High"


print("\nUPDATED STATE")
print(state.get_summary())


print("\nMISSING FIELDS")
print(state.get_missing_fields())


print("\nIS COMPLETE?")
print(state.is_complete())