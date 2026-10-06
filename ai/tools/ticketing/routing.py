
from pathlib import Path
from openpyxl import load_workbook


# Project root: Darpan 2.0/
PROJECT_ROOT = Path(__file__).resolve().parents[3]
EXCEL_FILE = PROJECT_ROOT / "data" / "ticket_routing.xlsx"


def normalize(value):
    """Normalize text for comparisons."""
    return " ".join(str(value or "").strip().lower().split())

def normalize_location_key(value):
    """
    Convert UI-friendly location names to the short location names
    used in the routing Excel file.
    """

    value = normalize(value)

    aliases = {
        "mundra vgpl 1": "vgpl1",
        "mundra vgpl 2": "vgpl2",
        "mundra vmpl 1": "vmpl1",
        "mundra vmpl 2": "vmpl2",
        "mundra vrpl": "vrpl",
    }

    return aliases.get(value, value)

def load_routing_rows():
    """Read the routing table from Excel."""
    if not EXCEL_FILE.exists():
        raise FileNotFoundError(
            f"Routing Excel file not found: {EXCEL_FILE}"
        )

    workbook = load_workbook(
        EXCEL_FILE,
        data_only=True,
        read_only=True
    )

    try:
        sheet = workbook.active
        rows = sheet.iter_rows(values_only=True)

        headers = next(rows, None)

        if not headers:
            raise ValueError(
                "Routing Excel sheet is empty."
            )

        headers = [normalize(h) for h in headers]

        required = [
            "ticket id",
            "group name",
            "ticket type",
            "group id",
            "location",
            "department",
        ]

        missing = [
            h for h in required
            if h not in headers
        ]

        if missing:
            raise ValueError(
                f"Missing required Excel columns: {missing}"
            )

        indexes = {
            header: headers.index(header)
            for header in required
        }

        records = []

        for row in rows:
            if not row or not any(
                v is not None for v in row
            ):
                continue

            record = {
                key: row[index]
                for key, index in indexes.items()
            }

            records.append(record)

        return records

    finally:
        workbook.close()


def get_departments():
    """
    Return unique department names from the routing Excel file.
    Department names are taken directly from the workbook.
    """

    records = load_routing_rows()

    departments = []

    for row in records:
        department = str(
            row["department"] or ""
        ).strip()

        if department and department not in departments:
            departments.append(department)

    return sorted(departments, key=str.lower)


def location_matches(
    excel_location,
    selected_location
):
    """Check whether an Excel routing location matches the user selection."""

    excel_loc = normalize(excel_location)
    selected_loc = normalize(selected_location)

    if not excel_loc or not selected_loc:
        return False

    # Global routes
    if excel_loc == "all":
        return True

    # HR routing rule
    if excel_loc == "all except shantigram":
        return "shantigram" not in selected_loc

    # Convert UI location to routing/Excel location name.
    selected_location_key = normalize_location_key(
        selected_location
    )

    # Excel may contain multiple locations:
    # VGPL1, VGPL2, VMPL1, VMPL2, VRPL
    excel_locations = [
        normalize_location_key(part)
        for part in str(excel_location).split(",")
        if normalize(part)
    ]

    # Exact match against an individual Excel location.
    if selected_location_key in excel_locations:
        return True

    # Preserve support for existing exact/contained location rules.
    return (
        selected_loc == excel_loc
        or selected_loc in excel_loc
        or excel_loc in selected_loc
    )


def find_route(
    department,
    request_type,
    location,
    group_hint=None,
):
    """
    Find a routing record using the Excel mapping.

    Priority:
    1. Exact location match
    2. Other valid location rules such as "All"
    3. Raise error if multiple routes still match

    Returns the exact Excel row as a dictionary.
    Raises ValueError when no route or multiple routes match.
    """

    department_key = normalize(department)
    request_type_key = normalize(request_type)
    group_key = normalize(group_hint)
    location_key = normalize(location)

    records = load_routing_rows()

    matches = []

    for row in records:

        if normalize(row["department"]) != department_key:
            continue

        if normalize(row["ticket type"]) != request_type_key:
            continue

        if not location_matches(
            row["location"],
            location
        ):
            continue

        # If a group/application was supplied,
        # require it to match the Excel Group Name.
        if group_key:
            if group_key not in normalize(
                row["group name"]
            ):
                continue

        matches.append(row)

    # ----------------------------------------------
    # No route found
    # ----------------------------------------------

    if not matches:
        raise ValueError(
            "No routing entry found for "
            f"Department='{department}', "
            f"Request Type='{request_type}', "
            f"Location='{location}', "
            f"Group='{group_hint or 'Not specified'}'."
        )

    # ----------------------------------------------
    # Prefer specific location over generic rules

    # ----------------------------------------------

    specific_location_matches = [
        row
        for row in matches
        if normalize(row["location"]) not in {
            "all",
            "all except shantigram",
        }
        and location_matches(
            row["location"],
            location
        )
    ]

    if len(specific_location_matches) == 1:
        return specific_location_matches[0]

    if len(specific_location_matches) > 1:
        matches = specific_location_matches

    # ----------------------------------------------
    # Multiple routes still matched
    # ----------------------------------------------

    if len(matches) > 1:

        groups = sorted({
            str(row["group name"])
            for row in matches
        })

        raise ValueError(
            "Multiple routing entries matched. "
            "Please clarify the application or resolver group: "
            + ", ".join(groups)
        )

    return matches[0]