from __future__ import annotations

import html
import re

import requests

from app.models import JobApplication


def fetch_jobs(board_token: str, company: str) -> list[JobApplication]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    response = requests.get(url, params={"content": "true"}, timeout=30)
    response.raise_for_status()
    jobs: list[JobApplication] = []
    for item in response.json().get("jobs", []):
        description = re.sub(r"<[^>]+>", " ", html.unescape(item.get("content", "")))
        jobs.append(
            JobApplication(
                title=item["title"],
                company=company,
                location=item.get("location", {}).get("name", ""),
                source="greenhouse",
                job_url=item["absolute_url"],
                application_url=item["absolute_url"],
                description=re.sub(r"\s+", " ", description).strip(),
            )
        )
    return jobs
