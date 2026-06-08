from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")


def _csv_env(name: str, default: str = "") -> set[str]:
    return {item.strip().lower() for item in os.getenv(name, default).split(",") if item.strip()}


@dataclass(slots=True)
class Settings:
    database_path: Path = field(
        default_factory=lambda: Path(os.getenv("DATABASE_PATH", ROOT_DIR / "data" / "job_agent.db"))
    )
    output_dir: Path = field(
        default_factory=lambda: Path(os.getenv("OUTPUT_DIR", ROOT_DIR / "outputs"))
    )
    profile_path: Path = field(
        default_factory=lambda: Path(os.getenv("PROFILE_PATH", ROOT_DIR / "profile" / "sanat_profile.yaml"))
    )
    answers_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("PREAPPROVED_ANSWERS_PATH", ROOT_DIR / "profile" / "preapproved_answers.yaml")
        )
    )
    sources_path: Path = field(
        default_factory=lambda: Path(
            os.getenv("SOURCES_PATH", ROOT_DIR / "profile" / "sources.yaml")
        )
    )
    score_threshold: float = field(default_factory=lambda: float(os.getenv("AUTO_SUBMIT_SCORE_THRESHOLD", "65")))
    auto_submit_enabled: bool = field(
        default_factory=lambda: os.getenv("AUTO_SUBMIT_ENABLED", "false").lower() == "true"
    )
    allowed_company_domains: set[str] = field(
        default_factory=lambda: _csv_env("ALLOWED_COMPANY_DOMAINS")
    )
    gmail_sender: str = field(default_factory=lambda: os.getenv("GMAIL_SENDER", ""))
    gmail_recipient: str = field(
        default_factory=lambda: os.getenv("GMAIL_RECIPIENT", "sanat.konda4@gmail.com")
    )
    gmail_credentials_path: str = field(default_factory=lambda: os.getenv("GMAIL_CREDENTIALS_PATH", ""))
    gmail_token_path: str = field(default_factory=lambda: os.getenv("GMAIL_TOKEN_PATH", ""))
    email_poll_interval_minutes: int = field(
        default_factory=lambda: int(os.getenv("EMAIL_POLL_INTERVAL_MINUTES", "10"))
    )
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))


settings = Settings()
