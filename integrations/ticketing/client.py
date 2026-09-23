import os

import requests
from dotenv import load_dotenv


load_dotenv()


class TicketingClient:

    def __init__(self):

        self.base_url = os.getenv(
            "TICKETING_BASE_URL"
        )

        self.pat = os.getenv(
            "TICKETING_PAT"
        )

        self.source = os.getenv(
            "TICKETING_SOURCE",
            "RPA"
        )

        self.requester = os.getenv(
            "TICKETING_REQUESTER"
        )

        self.actor = os.getenv(
            "TICKETING_ACTOR"
        )

        if not self.base_url:
            raise ValueError(
                "TICKETING_BASE_URL is not configured."
            )

        if not self.pat:
            raise ValueError(
                "TICKETING_PAT is not configured."
            )

    def create_ticket(
        self,
        title,
        description,
        ticket_type_id,
        priority,
        requester=None,
        actor=None,
    ):

        url = (
            f"{self.base_url}"
            "/api/itsm/v1/tickets"
        )

        headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        payload = {
            "title": title,
            "description": description,
            "source": self.source,
            "ticketType": {
                "id": ticket_type_id
            },
            "priority": {
                "name": priority
            },
            "requester": (
                requester
                or self.requester
            ),
            "actor": (
                actor
                or self.actor
            ),
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    def get_my_tickets(
        self,
        requester_email=None,
        include_closed=True,
        size=10,
    ):
        url = f"{self.base_url}/api/itsm/v1/tickets"

        headers = {
            "Authorization": f"Bearer {self.pat}",
            "Accept": "application/json",
        }

        params = {
            "requesterEmail": requester_email or self.requester,
            "includeClosed": str(include_closed).lower(),
            "size": size,
            "sort": "createdDate,desc",
        }

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    def get_ticket_by_id(self, ticket_id):
        url = f"{self.base_url}/api/itsm/v1/tickets/{ticket_id}"

        headers = {
            "Authorization": f"Bearer {self.pat}",
            "Accept": "application/json",
        }

        response = requests.get(
            url,
            headers=headers,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    def search_ticket(self, ticket_number):
        url = f"{self.base_url}/api/itsm/v1/tickets"

        headers = {
            "Authorization": f"Bearer {self.pat}",
            "Accept": "application/json",
        }

        params = {
            "search": ticket_number,
            "size": 10,
        }

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()