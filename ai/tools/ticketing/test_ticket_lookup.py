from ai.tools.ticketing.ticketing_tool import TicketingTool

tool = TicketingTool()

result = tool.get_ticket_by_number("INCS-061")

print("\nTICKET LOOKUP RESULT:")
print(result)