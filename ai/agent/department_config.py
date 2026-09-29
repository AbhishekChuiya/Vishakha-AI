DEPARTMENT_REQUEST_TYPES = {
    "Safety": [
        "Incident Request",
        "Service Request",
    ],

    "Security": [
        "Incident Request",
    ],

    "Admin": [
        "Incident Request",
        "Service Request",
    ],

    "Branding": [
        "Incident Request",
        "Service Request",
        "Change Management",
        "Request for Information",
    ],

    "HR": [
        "Incident Request",
        "Service Request",
    ],

    "Insurance": [
        "Service Request",
    ],

    "Finance": [
        "Service Request",
    ],

    "Risk Compliance": [
        "Service Request",
    ],

    "Projects": [
        "Change Management",
    ],

    "Strategy": [
        "Service Request",
    ],

    "IT": [
        "Service Request",
        "Incident Request",
    ],
}


def get_request_types(department):
    """
    Return the request types available for a department.
    """

    if not department:
        return []

    return DEPARTMENT_REQUEST_TYPES.get(department, [])