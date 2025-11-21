import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables for local configuration overrides.
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Minimal configuration needed for a local-only app."""

    SECRET_KEY = os.getenv("SECRET_KEY", "jarvisdnd-local-secret")

    _default_image_dir = BASE_DIR / "images"
    IMAGE_DOWNLOAD_DIR = Path(
        os.getenv("IMAGE_DOWNLOAD_DIR", str(_default_image_dir))
    ).expanduser().resolve()