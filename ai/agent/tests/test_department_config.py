from ai.agent.department_config import (
    DEPARTMENT_REQUEST_TYPES,
    get_request_types,
)


def main():
    print("\n===== DEPARTMENT REQUEST TYPE TEST =====\n")

    for department, request_types in DEPARTMENT_REQUEST_TYPES.items():
        result = get_request_types(department)

        print(f"{department}")
        print(f"  {result}")
        print()

    print("===== INDIVIDUAL TESTS =====\n")

    test_departments = [
        "IT",
        "Safety",
        "Security",
        "Branding",
        "Projects",
        "Strategy",
    ]

    for department in test_departments:
        print(
            f"{department} -> "
            f"{get_request_types(department)}"
        )


if __name__ == "__main__":
    main()