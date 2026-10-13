import os
import requests
from dotenv import load_dotenv
import json
import re
import unicodedata
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
        impact=None,
        start_date=None,
        custom_fields=None,
        group_id=None,
        category=None,
        subcategory=None,
        location=None,
    ):  
        
        url = f"{self.base_url}/api/itsm/v1/tickets"

        headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Resolve Category, Subcategory and Location IDs
        category_data = None
        subcategory_data = None
        location_data = None

        if category:
            category_data = self.get_category(
                ticket_type_id,
                category,
            )

        if subcategory:
            if not category_data:
                raise ValueError(
                    "Category is required to resolve subcategory."
                )

            subcategory_data = self.get_subcategory(
                category_data["id"],
                subcategory,
            )

        if location:
            location_data = self.get_location(
                location
            )

        # Do not log employee identities or ticket payloads.

        # 1. Create the payload FIRST
        payload = {
            "title": title,
            "description": description,
            "source": self.source,
            "ticketType": {"id": ticket_type_id},
            "priority": {"name": priority},
            "requester": requester,
            "actor": actor,
        }

        if category_data:
            payload["category"] = {
                "id": int(category_data["id"])
            }

        if subcategory_data:
            payload["subCategory"] = {
                "id": int(subcategory_data["id"])
            }

        if location_data:
            payload["location"] = {
                "id": int(location_data["id"])
            }

        # Add resolver group if provided
        if group_id is not None:
            payload["group"] = {
                "id": int(group_id)
            }

        # Add dynamic custom fields
        ticket_custom_fields = {}

        # Allow caller to provide additional custom fields
        if custom_fields:
            ticket_custom_fields.update(custom_fields)

        # Incident custom fields
        if impact:
            ticket_custom_fields["impact"] = impact

        if start_date:
            ticket_custom_fields["start_date"] = start_date

        if ticket_custom_fields:
            payload["customFields"] = ticket_custom_fields

        # Do not print ticket descriptions, custom fields, or requester details.

        # 4. Send API request
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=30,
        )

        # Avoid logging raw SEP responses that may contain employee information.

        response.raise_for_status()

        return response.json()
    
    def _lookup_exact_name(self, endpoint, name, params=None):
        """
        Search a lookup endpoint and return the exact
        case-insensitive name match.
        """

        url = f"{self.base_url}/api/itsm/v1/lookup/{endpoint}"

        headers = {
            "Authorization": f"Bearer {self.pat}",
            "Accept": "application/json",
        }

        query_params = params.copy() if params else {}

        query_params["search"] = name
        query_params["size"] = 100

        response = requests.get(
            url,
            headers=headers,
            params=query_params,
            timeout=30,
        )

        response.raise_for_status()

        data = response.json()

        results = data.get("content", [])

        # IMPORTANT:
        # Search API may return similar values.
        # Example: WIFI may return Guest-WIFI and WIFI.
        # Therefore select only the exact name.
        for item in results:
            if (
                str(item.get("name", "")).strip().lower()
                == str(name).strip().lower()
            ):
                return item

        available_names = [
            str(item.get("name"))
            for item in results
        ]

        raise ValueError(
            f"Exact {endpoint} match not found for "
            f"'{name}'. API returned: {available_names}"
        )


    @staticmethod
    def _canonical_lookup_name(value):
        """Normalize equivalent AND/& spelling, not arbitrary similar names."""
        text = unicodedata.normalize("NFKC", str(value or "")).casefold()
        text = text.replace("&", " and ")
        return " ".join(re.findall(r"[\w]+", text))

    def _lookup_subcategory_without_search(self, category_id, name):
        """SEP's search misses aliases such as 'and' versus '&'.

        Fetch all active subcategories of this category and accept ONLY a
        unique canonical exact name. Never guess an ID.
        """
        url = f"{self.base_url}/api/itsm/v1/lookup/subcategories"
        headers = {
            "Authorization": f"Bearer {self.pat}",
            "Accept": "application/json",
        }
        target = self._canonical_lookup_name(name)
        matches = []
        page = 0
        while True:
            response = requests.get(
                url,
                headers=headers,
                params={
                    "categoryId": int(category_id),
                    "includeInactive": "false",
                    "size": 100,
                    "page": page,
                },
                timeout=30,
            )
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, dict) or not isinstance(body.get("content"), list):
                raise ValueError("SEP returned an unexpected subcategory lookup response.")
            matches.extend(item for item in body["content"]
                           if isinstance(item, dict)
                           and self._canonical_lookup_name(item.get("name")) == target)
            total_pages = body.get("totalPages")
            if total_pages is not None:
                if page + 1 >= int(total_pages):
                    break
            elif len(body["content"]) < 100:
                break
            page += 1
            if page >= 100:
                raise ValueError("SEP subcategory lookup exceeded safe page limit.")
        ids = {str(item.get("id")) for item in matches}
        if len(ids) == 1:
            return matches[0]
        if matches:
            raise ValueError(f"Ambiguous SEP subcategory '{name}' in category {category_id}.")
        raise ValueError(
            f"SEP subcategory '{name}' was not found under category {category_id}. "
            "Please check the available subcategories in SEP."
        )


    def get_category(self, ticket_type_id, category_name):
        return self._lookup_exact_name(
            endpoint="categories",
            name=category_name,
            params={
                "ticketTypeId": int(ticket_type_id),
                "includeInactive": "false",
            },
        )


    def get_subcategory(self, category_id, subcategory_name):
        try:
            return self._lookup_exact_name(
                endpoint="subcategories",
                name=subcategory_name,
                params={
                    "categoryId": int(category_id),
                    "includeInactive": "false",
                },
            )
        except ValueError as exc:
            # Fallback only for a normal lookup miss, not for other errors.
            if not str(exc).startswith("Exact subcategories match not found"):
                raise
            return self._lookup_subcategory_without_search(category_id, subcategory_name)

    def resolve_category_subcategory(
        self,
        ticket_type_id,
        category_name,
        subcategory_name=None,
    ):
        """
        Resolve category/subcategory names to their actual
        Service Excellence IDs.
        """

        category_data = self.get_category(
            ticket_type_id,
            category_name,
        )

        result = {
            "category_id": int(category_data["id"]),
            "category_name": category_data.get(
                "name",
                category_name,
            ),
            "subcategory_id": None,
            "subcategory_name": None,
        }

        if subcategory_name:

            subcategory_data = self.get_subcategory(
                category_data["id"],
                subcategory_name,
            )

            result["subcategory_id"] = int(
                subcategory_data["id"]
            )

            result["subcategory_name"] = (
                subcategory_data.get(
                    "name",
                    subcategory_name,
                )
            )

        return result

    def get_location(self, location_name):
        return self._lookup_exact_name(
            endpoint="locations",
            name=location_name,
        )
    
    def get_my_tickets(
        self,
        requester_email=None,
        include_closed=True,
        status_ids=None,
        ticket_type_id=None,
        group_ids=None,
        category_id=None,
        subcategory_id=None,
        size=20,
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
            "sort": "createdAt,desc",
        }

        if status_ids:
            params["statusId"] = status_ids

        if ticket_type_id:
            params["ticketTypeId"] = ticket_type_id

        if group_ids:
            params["groupId"] = group_ids

        if category_id is not None:
            params["categoryId"] = category_id

        if subcategory_id is not None:
            params["subCategoryId"] = subcategory_id

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()
        
    def get_all_tickets(
        self,
        search_query=None,
        include_closed=True,
        status_ids=None,
        ticket_type_id=None,
        group_ids=None,
        category_id=None,
        subcategory_id=None,
        size=20,
    ):
        url = f"{self.base_url}/api/itsm/v1/tickets"

        headers = {
            "Authorization": f"Bearer {self.pat}",
            "Accept": "application/json",
        }

        params = {
            "includeClosed": str(include_closed).lower(),
            "size": size,
            "sort": "createdAt,desc",
        }

        if search_query:
            params["search"] = search_query

        if status_ids:
            params["statusId"] = status_ids

        if ticket_type_id:
            params["ticketTypeId"] = ticket_type_id

        if group_ids:
            params["groupId"] = group_ids

        if category_id:
            params["categoryId"] = category_id

        if subcategory_id:
            params["subCategoryId"] = subcategory_id

        print("Get All Tickets Search Query:", search_query)
        print("Get All Tickets Include Closed:", include_closed)
        print("Get All Tickets Status IDs:", status_ids)
        print("Get All Tickets Ticket Type ID:", ticket_type_id)
        print("Get All Tickets Group IDs:", group_ids)
        print("Get All Tickets Category ID:", category_id)
        print("Get All Tickets Subcategory ID:", subcategory_id)

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
            "includeClosed": "true",
            "size": 25,
            "sort": "createdAt,desc",
        }

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    def search_tickets(
        self,
        search_query,
        include_closed=True,
        status_ids=None,
        ticket_type_id=None,
        group_ids=None,
        size=20,
    ):
        url = f"{self.base_url}/api/itsm/v1/tickets"

        headers = {
            "Authorization": f"Bearer {self.pat}",
            "Accept": "application/json",
        }

        params = {
            "search": search_query,
            "includeClosed": str(include_closed).lower(),
            "size": size,
            "sort": "createdAt,desc",
        }

        if status_ids:
            params["statusId"] = status_ids

        if ticket_type_id:
            params["ticketTypeId"] = ticket_type_id

        if group_ids:
            params["groupId"] = group_ids

        print("Search All Tickets Query:", search_query)
        print(
            "Search All Tickets Include Closed:",
            include_closed,
        )
        print(
            "Search All Tickets Status IDs:",
            status_ids,
        )
        print(
            "Search All Tickets Ticket Type ID:",
            ticket_type_id,
        )

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()

    def search_my_tickets(
        self,
        search_query,
        requester_email=None,
        include_closed=True,
        status_ids=None,
        ticket_type_id=None,
        group_ids=None,
        category_id=None,
        subcategory_id=None,
        size=20,
    ):
        url = f"{self.base_url}/api/itsm/v1/tickets"

        headers = {
            "Authorization": f"Bearer {self.pat}",
            "Accept": "application/json",
        }

        params = {
            "search": search_query,
            "requesterEmail": requester_email or self.requester,
            "includeClosed": str(include_closed).lower(),
            "size": size,
            "sort": "createdAt,desc",
        }

        if status_ids:
            params["statusId"] = status_ids

        if ticket_type_id:
            params["ticketTypeId"] = ticket_type_id

        if group_ids:
            params["groupId"] = group_ids

        if category_id is not None:
            params["categoryId"] = category_id

        if subcategory_id is not None:
            params["subCategoryId"] = subcategory_id

        print(
            "Search My Tickets Requester Email:",
            requester_email or self.requester
        )
        print(
            "Search My Tickets Include Closed:",
            include_closed
        )
        print(
            "Search My Tickets Status IDs:",
            status_ids
        )
        print(
            "Search My Tickets Ticket Type ID:",
            ticket_type_id
        )

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30,
        )

        response.raise_for_status()

        return response.json()