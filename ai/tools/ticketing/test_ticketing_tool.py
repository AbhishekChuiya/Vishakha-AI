from ai.tools.ticketing.ticketing_tool import TicketingTool


tool = TicketingTool()


result = tool.create_ticket(
    category="Laptop Repair",
    description="My laptop screen is not working",
    location="Ahmedabad Plant",
    priority="High",
)


print("\nTICKETING TOOL RESULT:")
print(result)