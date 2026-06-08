from __future__ import annotations

import requests

from app.models import JobApplication


def fetch_jobs(board_name: str, company: str) -> list[JobApplication]:
    response = requests.get(
        f"https://api.ashbyhq.com/posting-api/job-board/{board_name}",
        timeout=30,
    )
    response.raise_for_status()
    jobs: list[JobApplication] = []
    for item in response.json().get("jobs", []):
        jobs.append(
            JobApplication(
                title=item["title"],
                company=company,
                location=item.get("location", ""),
                source="ashby",
                job_url=item["jobUrl"],
                application_url=item.get("applyUrl", item["jobUrl"]),
                description=item.get("descriptionPlain", ""),
            )
        )
    return jobs
