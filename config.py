import os
from dotenv import load_dotenv

# Load environment variables for local configuration overrides.
load_dotenv()


class Config:
    """Minimal configuration needed for a local-only app."""

    SECRET_KEY = os.getenv("SECRET_KEY", "jarvisdnd-local-secret")