
from ai.tools.ticketing.ticketing_tool import TicketingTool


class TicketAnalytics:

    # Verified IT Department ticket-type mapping
    IT_TICKET_TYPES = {
        "Incident Request": 56,
        "Service Request": 55,
    }

    # Status IDs observed in Service Excellence
    STATUS_IDS = {
        "Resolved": 42,
        "Closed": 43,
        "Cancelled": 44,
    }

    def __init__(self):
        self.tool = TicketingTool()

    def _count(
        self,
        ticket_type_id,
        include_closed=True,
        status_ids=None,
    ):
        response = self.tool.get_all_tickets(
            ticket_type_id=ticket_type_id,
            include_closed=include_closed,
            status_ids=status_ids,
            size=1,
        )

        total = response.get("totalElements")

        if total is None:
            raise ValueError(
                "Ticket API did not provide totalElements"
            )

        return int(total)

    def get_it_summary(self):

        summary = {
            "department": "IT Department",
            "total_tickets": 0,
            "open_tickets": 0,
            "resolved_tickets": 0,
            "closed_tickets": 0,
            "cancelled_tickets": 0,
            "by_request_type": {},
        }

        for request_type, ticket_type_id in (
            self.IT_TICKET_TYPES.items()
        ):

            total = self._count(
                ticket_type_id=ticket_type_id
            )

            # Matches the API's includeClosed=false filter.
            open_count = self._count(
                ticket_type_id=ticket_type_id,
                include_closed=False,
            )

            resolved = self._count(
                ticket_type_id=ticket_type_id,
                status_ids=[self.STATUS_IDS["Resolved"]],
            )

            closed = self._count(
                ticket_type_id=ticket_type_id,
                status_ids=[self.STATUS_IDS["Closed"]],
            )

            cancelled = self._count(
                ticket_type_id=ticket_type_id,
                status_ids=[self.STATUS_IDS["Cancelled"]],
            )

            summary["by_request_type"][request_type] = {
                "total": total,
                "open": open_count,
                "resolved": resolved,
                "closed": closed,
                "cancelled": cancelled,
            }

            summary["total_tickets"] += total
            summary["open_tickets"] += open_count
            summary["resolved_tickets"] += resolved
            summary["closed_tickets"] += closed
            summary["cancelled_tickets"] += cancelled

        return summary
