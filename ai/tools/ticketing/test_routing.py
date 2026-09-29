
from ai.tools.ticketing.routing import find_route


def test_sap_basis_service_request():
    route = find_route(
        department="IT",
        request_type="Service Request",
        location="HO Shantigram",
        group_hint="SAP BASIS",
    )

    print("SAP BASIS Service Request")
    print("Ticket ID:", route["ticket id"])
    print("Group Name:", route["group name"])
    print("Group ID:", route["group id"])
    print("Location:", route["location"])


if __name__ == "__main__":
    test_sap_basis_service_request()