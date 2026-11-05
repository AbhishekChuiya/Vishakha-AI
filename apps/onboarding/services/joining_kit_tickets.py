
# from django.db import transaction

# from ai.tools.ticketing.ticketing_tool import TicketingTool
# from apps.onboarding.models import JoiningKitTicket


# # These values are based on the mappings already present in your project.
# # Add or change mappings only after checking the actual SEP catalog.
# ASSET_TICKET_MAPPING = {
#     "laptop": {
#         "department": "IT Department",
#         "category": "Hardware",
#         "subcategory": "Laptop Machine",
#     },
#     "desktop": {
#         "department": "IT Department",
#         "category": "Hardware",
#         "subcategory": "Desktop Machine",
#     },
#     "monitor": {
#         "department": "IT Department",
#         "category": "Hardware",
#         "subcategory": "Monitor Display",
#     },
#     "keyboard_mouse": {
#         "department": "IT Department",
#         "category": "Hardware",
#         "subcategory": "Wireless Mouse-Keyboard (Combo)",
#     },
#     "tablet": {
#         "department": "IT Department",
#         "category": "Hardware",
#         "subcategory": "Tablet",
#     },
#     "email": {
#         "department": "IT Department",
#         "category": "Messaging Server",
#         "subcategory": "Generic Mail ID Creation-Deletion",
#     },
#     "sap": {
#         "department": "IT Department",
#         "category": "Application",
#         "subcategory": "SAP BASIS",
#     },
#     "peoplestrong": {
#         "department": "HR Department",
#         "category": "Software & Tools",
#         "subcategory": "People Strong",
#     },
#     "software": {
#         "department": "IT Department",
#         "category": "Software & Tools",
#         "subcategory": "Other Application",
#     },
#     "safety_shoes": {
#         "department": "Safety",
#         "category": "PPE Compliance",
#         "subcategory": "PPE Issuance",
#     },
#     "helmet": {
#         "department": "Safety",
#         "category": "PPE Compliance",
#         "subcategory": "PPE Issuance",
#     },
#     "safety_glasses": {
#         "department": "Safety",
#         "category": "PPE Compliance",
#         "subcategory": "PPE Issuance",
#     },
#     "uniform": {
#         "department": "Admin",
#         "category": "PPE Compliance",
#         "subcategory": "PPE Issuance",
#     },
#     "other_ppe": {
#         "department": "Safety",
#         "category": "PPE Compliance",
#         "subcategory": "PPE Issuance",
#     },
# }


# def _asset_labels():
#     # Import locally to avoid a module-level circular import.
#     from apps.onboarding.views import ASSET_OPTIONS
#     return dict(ASSET_OPTIONS)


# def _default_description(kit_request, asset_label):
#     joinee = kit_request.joinee

#     return (
#         "Joining Kit asset request\n"
#         f"Joinee: {joinee.full_name}\n"
#         f"Employee code: {joinee.employee_code}\n"
#         f"Designation: {joinee.designation}\n"
#         f"Department: {joinee.department}\n"
#         f"Level: {joinee.level}\n"
#         f"Grade: {joinee.grade}\n"
#         f"Asset requested: {asset_label}\n"
#         f"Required by: {kit_request.required_by}\n"
#         f"Manager notes: {kit_request.notes or 'None'}"
#     )


# def build_ticket_previews(kit_request):
#     """
#     Build editable ticket details for the on-page review step.
#     This function does not call SEP or create tickets.
#     """
#     labels = _asset_labels()
#     previews = []

#     existing_records = {
#         ticket.asset_key: ticket
#         for ticket in kit_request.generated_tickets.all()
#     }

#     for asset_key in kit_request.selected_assets:
#         asset_label = labels.get(asset_key, asset_key)
#         mapping = ASSET_TICKET_MAPPING.get(asset_key, {})
#         existing = existing_records.get(asset_key)

#         previews.append({
#             "asset_key": asset_key,
#             "asset_label": asset_label,
#             "department": mapping.get("department", ""),
#             "category": mapping.get("category", ""),
#             "subcategory": mapping.get("subcategory", ""),
#             "description": _default_description(
#                 kit_request, asset_label
#             ),
#             "location": (
#                 kit_request.joinee.plant_location or ""
#             ).strip(),
#             "priority": "Medium",
#             "request_type": "Service Request",
#             "target_date": (
#                 kit_request.joinee.joining_date.isoformat()
#                 if kit_request.joinee.joining_date
#                 else ""
#             ),
#             "business_justification": (
#                 f"Joining Kit provisioning for "
#                 f"{kit_request.joinee.full_name} "
#                 f"({kit_request.joinee.employee_code})"
#             ),
#             "already_created": bool(
#                 existing and existing.status == "created"
#             ),
#             "mapping_missing": not bool(mapping),
#         })

#     return previews


# def create_joining_kit_tickets(kit_request, ticket_overrides=None):
#     """
#     Create one SEP ticket per selected asset.

#     ticket_overrides is a dictionary keyed by asset key.
#     Successful local ticket records are never recreated.
#     """
#     ticket_overrides = ticket_overrides or {}
#     tool = TicketingTool()
#     labels = _asset_labels()
#     results = []

#     for asset_key in kit_request.selected_assets:
#         asset_label = labels.get(asset_key, asset_key)
#         mapping = dict(ASSET_TICKET_MAPPING.get(asset_key, {}))
#         override = ticket_overrides.get(asset_key, {})

#         # Only accept the fields that the manager is allowed to edit.
#         allowed_fields = {
#             "department",
#             "category",
#             "subcategory",
#             "description",
#             "location",
#             "priority",
#             "request_type",
#             "target_date",
#             "business_justification",
#         }
#         for field in allowed_fields:
#             if field in override:
#                 mapping[field] = str(override[field]).strip()

#         with transaction.atomic():
#             ticket_record, _ = JoiningKitTicket.objects.get_or_create(
#                 joining_kit_request=kit_request,
#                 asset_key=asset_key,
#                 defaults={
#                     "asset_label": asset_label,
#                     "status": "pending",
#                 },
#             )

#             if ticket_record.status == "created":
#                 results.append(ticket_record)
#                 continue

#             # Do not automatically retry an uncertain API attempt.
#             if ticket_record.status == "creating":
#                 results.append(ticket_record)
#                 continue

#             ticket_record.asset_label = asset_label
#             ticket_record.status = "creating"
#             ticket_record.error_message = ""
#             ticket_record.save()

#         try:
#             required_fields = (
#                 "department",
#                 "category",
#                 "subcategory",
#                 "description",
#                 "location",
#                 "priority",
#                 "request_type",
#             )
#             missing = [
#                 field for field in required_fields
#                 if not mapping.get(field)
#             ]
#             if missing:
#                 raise ValueError(
#                     "Please complete these ticket fields: "
#                     + ", ".join(missing)
#                 )

#             response = tool.create_ticket(
#                 department=mapping["department"],
#                 category=mapping["category"],
#                 subcategory=mapping["subcategory"],
#                 description=mapping["description"],
#                 location=mapping["location"],
#                 priority=mapping["priority"],
#                 requester=kit_request.manager_email,
#                 actor=kit_request.manager_email,
#                 request_type=mapping["request_type"],
#                 target_date=mapping.get("target_date") or None,
#                 business_justification=(
#                     mapping.get("business_justification") or ""
#                 ),
#             )

#             if not isinstance(response, dict):
#                 raise ValueError(
#                     "Unexpected SEP response format. "
#                     "Check the API response before retrying."
#                 )

#             ticket_number = (
#                 response.get("ticketNumber")
#                 or response.get("ticket_number")
#                 or response.get("number")
#                 or ""
#             )
#             ticket_id = response.get("id", "")

#             if not ticket_number and not ticket_id:
#                 raise ValueError(
#                     "SEP did not return a ticket number or ID. "
#                     "Check the SEP response before retrying."
#                 )

#             ticket_record.ticket_number = str(ticket_number)
#             ticket_record.ticket_id = str(ticket_id)
#             ticket_record.status = "created"
#             ticket_record.error_message = ""
#             ticket_record.save()

#         except Exception as exc:
#             ticket_record.status = "failed"
#             ticket_record.error_message = str(exc)[:2000]
#             ticket_record.save()

#         results.append(ticket_record)

#     return results

from django.db import transaction

from ai.tools.ticketing.ticketing_tool import TicketingTool
from apps.onboarding.models import JoiningKitTicket


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
        "department": "HR Department",
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
        "department": "Admin",
        "category": "PPE Compliance",
        "subcategory": "PPE Issuance",
    },
    "other_ppe": {
        "department": "Safety",
        "category": "PPE Compliance",
        "subcategory": "PPE Issuance",
    },
}


def _asset_labels():
    # Local import avoids a circular import with views.py.
    from apps.onboarding.views import ASSET_OPTIONS

    return dict(ASSET_OPTIONS)


def _default_description(kit_request, asset_label):
    joinee = kit_request.joinee

    return (
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


def build_ticket_previews(kit_request):
    """
    Build editable ticket details without creating tickets.
    """
    labels = _asset_labels()
    previews = []

    existing_records = {
        ticket.asset_key: ticket
        for ticket in kit_request.generated_tickets.all()
    }

    for asset_key in kit_request.selected_assets:
        asset_label = labels.get(asset_key, asset_key)
        mapping = ASSET_TICKET_MAPPING.get(asset_key, {})
        existing = existing_records.get(asset_key)

        previews.append({
            "asset_key": asset_key,
            "asset_label": asset_label,
            "department": mapping.get("department", ""),
            "category": mapping.get("category", ""),
            "subcategory": mapping.get("subcategory", ""),
            "description": _default_description(
                kit_request,
                asset_label,
            ),
            "location": (
                kit_request.joinee.plant_location or ""
            ).strip(),
            "priority": "Medium",
            "request_type": "Service Request",
            "target_date": (
                kit_request.joinee.joining_date.isoformat()
                if kit_request.joinee.joining_date
                else ""
            ),
            "business_justification": (
                f"Joining Kit provisioning for "
                f"{kit_request.joinee.full_name} "
                f"({kit_request.joinee.employee_code})"
            ),
            "already_created": bool(
                existing and existing.creation_status == "created"
            ),
            "mapping_missing": not bool(mapping),
        })

    return previews


def create_joining_kit_tickets(
    kit_request,
    ticket_overrides=None,
):
    """
    Create one SEP ticket per selected asset.

    Internal creation state is stored in creation_status.
    Actual SEP status is stored separately in status.
    """
    ticket_overrides = ticket_overrides or {}

    tool = TicketingTool()
    labels = _asset_labels()
    results = []

    for asset_key in kit_request.selected_assets:
        asset_label = labels.get(asset_key, asset_key)

        mapping = dict(
            ASSET_TICKET_MAPPING.get(asset_key, {})
        )

        override = ticket_overrides.get(asset_key, {})

        allowed_fields = {
            "department",
            "category",
            "subcategory",
            "description",
            "location",
            "priority",
            "request_type",
            "target_date",
            "business_justification",
        }

        for field in allowed_fields:
            if field in override:
                mapping[field] = str(
                    override[field]
                ).strip()

        with transaction.atomic():
            ticket_record, _ = JoiningKitTicket.objects.get_or_create(
                joining_kit_request=kit_request,
                asset_key=asset_key,
                defaults={
                    "asset_label": asset_label,
                    "creation_status": "pending",
                },
            )

            # Never recreate a ticket already created in SEP,
            # even if its actual SEP status is Cancelled or Closed.
            if ticket_record.creation_status == "created":
                results.append(ticket_record)
                continue

            # Avoid retrying an uncertain API attempt automatically.
            if ticket_record.creation_status == "creating":
                results.append(ticket_record)
                continue

            ticket_record.asset_label = asset_label
            ticket_record.creation_status = "creating"
            ticket_record.error_message = ""
            ticket_record.save(
                update_fields=[
                    "asset_label",
                    "creation_status",
                    "error_message",
                    "updated_at",
                ]
            )

        try:
            required_fields = (
                "department",
                "category",
                "subcategory",
                "description",
                "location",
                "priority",
                "request_type",
            )

            missing = [
                field
                for field in required_fields
                if not mapping.get(field)
            ]

            if missing:
                raise ValueError(
                    "Please complete these ticket fields: "
                    + ", ".join(missing)
                )

            response = tool.create_ticket(
                department=mapping["department"],
                category=mapping["category"],
                subcategory=mapping["subcategory"],
                description=mapping["description"],
                location=mapping["location"],
                priority=mapping["priority"],
                requester=kit_request.manager_email,
                actor=kit_request.manager_email,
                request_type=mapping["request_type"],
                target_date=mapping.get("target_date") or None,
                business_justification=(
                    mapping.get("business_justification") or ""
                ),
            )

            if not isinstance(response, dict):
                raise ValueError(
                    "Unexpected SEP response format. "
                    "Check the API response before retrying."
                )

            ticket_number = (
                response.get("ticketNumber")
                or response.get("ticket_number")
                or response.get("number")
                or ""
            )

            ticket_id = response.get("id", "")

            if not ticket_number and not ticket_id:
                raise ValueError(
                    "SEP did not return a ticket number or ID. "
                    "Check the SEP response before retrying."
                )

            ticket_record.ticket_number = str(ticket_number)
            ticket_record.ticket_id = str(ticket_id)
            ticket_record.creation_status = "created"
            ticket_record.error_message = ""

            # If SEP also returned a status during creation, save it.
            status_data = response.get("status")

            if isinstance(status_data, dict):
                ticket_record.status = str(
                    status_data.get("status") or ""
                ).strip()

                status_id = status_data.get("id")
                ticket_record.external_status_id = (
                    str(status_id)
                    if status_id is not None
                    else ""
                )

            ticket_record.save()

        except Exception as exc:
            ticket_record.creation_status = "failed"
            ticket_record.error_message = str(exc)[:2000]
            ticket_record.save(
                update_fields=[
                    "creation_status",
                    "error_message",
                    "updated_at",
                ]
            )

        results.append(ticket_record)

    return results