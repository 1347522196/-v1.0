from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .runtime import data_dir


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_DIR = data_dir()


@dataclass(frozen=True)
class Settings:
    database_path: Path = Path(
        os.getenv("AMAZON_DB_PATH", str(DEFAULT_DATA_DIR / "amazon_hardware.db"))
    )
    request_timeout_seconds: int = int(os.getenv("AMAZON_REQUEST_TIMEOUT", "20"))
    scraper_delay_seconds: float = float(os.getenv("AMAZON_SCRAPER_DELAY", "1.0"))
    default_marketplace: str = os.getenv("AMAZON_MARKETPLACE", "com")
    user_agent: str = os.getenv(
        "AMAZON_USER_AGENT",
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    )


settings = Settings()
