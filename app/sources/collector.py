from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.models import JobApplication
from app.sources import ashby, greenhouse, lever


def load_source_config(path: str | Path) -> dict[str, Any]:
    source_path = Path(path)
    if not source_path.exists():
        return {}
    return yaml.safe_load(source_path.read_text(encoding="utf-8")) or {}


def collect_configured_jobs(path: str | Path) -> list[JobApplication]:
    config = load_source_config(path)
    jobs: list[JobApplication] = []
    for board in config.get("greenhouse", []):
        jobs.extend(greenhouse.fetch_jobs(board["board_token"], board["company"]))
    for board in config.get("lever", []):
        jobs.extend(lever.fetch_jobs(board["company_slug"], board["company"]))
    for board in config.get("ashby", []):
        jobs.extend(ashby.fetch_jobs(board["board_name"], board["company"]))
    return jobs
