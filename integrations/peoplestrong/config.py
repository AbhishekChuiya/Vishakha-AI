
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class PeopleStrongConfig:
    base_url: str
    auth_url: str
    client_id: str
    client_secret: str
    api_key: str
    tenant_id: str
    timeout: int

    @classmethod
    def from_env(cls):
        return cls(
            base_url=os.getenv(
                "PEOPLESTRONG_BASE_URL", ""
            ).rstrip("/"),
            auth_url=os.getenv(
                "PEOPLESTRONG_AUTH_URL", ""
            ),
            client_id=os.getenv(
                "PEOPLESTRONG_CLIENT_ID", ""
            ),
            client_secret=os.getenv(
                "PEOPLESTRONG_CLIENT_SECRET", ""
            ),
            api_key=os.getenv(
                "PEOPLESTRONG_API_KEY", ""
            ),
            tenant_id=os.getenv(
                "PEOPLESTRONG_TENANT_ID", ""
            ),
            timeout=int(
                os.getenv("PEOPLESTRONG_TIMEOUT", "30")
            ),
        )
