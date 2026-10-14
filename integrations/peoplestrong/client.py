
from integrations.peoplestrong.config import PeopleStrongConfig


class PeopleStrongClient:
    """PeopleStrong HRMS integration entry point.

    API methods will be implemented after the official
    API documentation and authentication contract are reviewed.
    """

    def __init__(self):
        self.config = PeopleStrongConfig.from_env()

        if not self.config.base_url:
            raise ValueError(
                "PEOPLESTRONG_BASE_URL is not configured."
            )

    def health_check(self):
        raise NotImplementedError(
            "Implement after confirming the official "
            "PeopleStrong health/status endpoint."
        )
