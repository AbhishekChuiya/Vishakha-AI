
from django.db import transaction

from ai.tools.ticketing.ticketing_tool import TicketingTool
from apps.onboarding.models import JoiningKitTicket


# These names must match the existing Service Excellence catalog.
# Do not silently substitute a different category or subcategory.
ASSET_TICKET_MAPPING = {
    "laptop": {
        "department": "IT Department",
        "category": "Hardware",
        "subcategory": "Laptop Machine",
    },
    "desktop": {
        "department": "IT Department",
        "category": "Hardware",
        "subcategory": "Desktop Machine",
    },
    "monitor": {
        "department": "IT Department",
        "category": "Hardware",
        "subcategory": "Monitor Display",
    },
    "keyboard_mouse": {
        "department": "IT Department",
        "category": "Hardware",
        "subcategory": "Wireless Mouse-Keyboard (Combo)",
    },
    "tablet": {
        "department": "IT Department",
        "category": "Hardware",
        "subcategory": "Tablet",
    },
    "email": {
        "department": "IT Department",
        "category": "Messaging Server",
        "subcategory": "Generic Mail ID Creation-Deletion",
    },
    "sap": {
        "department": "IT Department",
        "category": "Application",
        "subcategory": "SAP BASIS",
    },
    "peoplestrong": {
        "department": "IT Department",
        "category": "Software & Tools",
        "subcategory": "People Strong",
    },
    "software": {
        "department": "IT Department",
        "category": "Software & Tools",
        "subcategory": "Other Application",
    },
    "safety_shoes": {
        "department": "Safety",
        "category": "PPE Compliance",
        "subcategory": "PPE Issuance",
    },
    "helmet": {
        "department": "Safety",
        "category": "PPE Compliance",
        "subcategory": "PPE Issuance",
    },
    "safety_glasses": {
        "department": "Safety",
        "category": "PPE Compliance",
        "subcategory": "PPE Issuance",
    },
    "uniform": {
        "department": "Safety",
        "category": "PPE Compliance",
        "subcategory": "PPE Issuance",
    },
    "other_ppe": {
        "department": "Safety",
        "category": "PPE Compliance",
        "subcategory": "PPE Issuance",
    },
}


def create_joining_kit_tickets(kit_request):
    """
    Create one Service Excellence ticket per selected asset.

    Existing ticket records are reused on subsequent calls.
    Failed attempts are retained for investigation/retry.
    """

    tool = TicketingTool()
    joinee = kit_request.joinee

    asset_labels = dict(
        __import__(
            "apps.onboarding.views",
            fromlist=["ASSET_OPTIONS"],
        ).ASSET_OPTIONS
    )

    results = []

    for asset_key in kit_request.selected_assets:
        asset_label = asset_labels.get(asset_key, asset_key)

        # Create the local record before making the external API call.
        with transaction.atomic():
            ticket_record, _ = JoiningKitTicket.objects.get_or_create(
                joining_kit_request=kit_request,
                asset_key=asset_key,
                defaults={
                    "asset_label": asset_label,
                    "status": "pending",
                },
            )

            # Do not create a second ticket for an already successful asset.
            if ticket_record.status == "created":
                results.append(ticket_record)
                continue

            # Avoid silently retrying an uncertain previous API attempt.
            if ticket_record.status == "creating":
                results.append(ticket_record)
                continue

            ticket_record.asset_label = asset_label
            ticket_record.status = "creating"
            ticket_record.error_message = ""
            ticket_record.save()

        mapping = ASSET_TICKET_MAPPING.get(asset_key)

        if not mapping:
            ticket_record.status = "failed"
            ticket_record.error_message = (
                f"No verified ticket mapping is configured for "
                f"'{asset_label}' ({asset_key})."
            )
            ticket_record.save()
            results.append(ticket_record)
            continue

        try:
            location = (joinee.plant_location or "").strip()
            if not location:
                raise ValueError(
                    "The joinee's plant location is missing."
                )

            description = (
                "Joining Kit asset request\n"
                f"Joinee: {joinee.full_name}\n"
                f"Employee code: {joinee.employee_code}\n"
                f"Designation: {joinee.designation}\n"
                f"Department: {joinee.department}\n"
                f"Level: {joinee.level}\n"
                f"Grade: {joinee.grade}\n"
                f"Asset requested: {asset_label}\n"
                f"Required by: {kit_request.required_by}\n"
                f"Manager notes: {kit_request.notes or 'None'}"
            )

            response = tool.create_ticket(
                category=mapping["category"],
                subcategory=mapping["subcategory"],
                description=description,
                location=location,
                priority="Medium",
                requester=kit_request.manager_email,
                actor=kit_request.manager_email,
                request_type="Service Request",
                department=mapping["department"],
                target_date=(
                    joinee.joining_date.isoformat()
                    if joinee.joining_date
                    else None
                ),
                business_justification=(
                    f"Joining Kit provisioning for "
                    f"{joinee.full_name} ({joinee.employee_code})"
                ),
            )

            # Adapt these keys if the API returns a different response shape.
            ticket_number = (
                response.get("ticketNumber")
                or response.get("ticket_number")
                or response.get("number")
                or ""
            )
            ticket_id = response.get("id", "")

            if not ticket_number and not ticket_id:
                raise ValueError(
                    "The API response did not include a ticket number or ID. "
                    "Check the response format before retrying."
                )

            ticket_record.ticket_number = str(ticket_number)
            ticket_record.ticket_id = str(ticket_id)
            ticket_record.status = "created"
            ticket_record.error_message = ""
            ticket_record.save()

        except Exception as exc:
            ticket_record.status = "failed"
            ticket_record.error_message = str(exc)[:2000]
            ticket_record.save()

        results.append(ticket_record)

    return results
