from __future__ import annotations

import requests

from app.models import JobApplication


def fetch_jobs(company_slug: str, company: str) -> list[JobApplication]:
    response = requests.get(
        f"https://api.lever.co/v0/postings/{company_slug}",
        params={"mode": "json"},
        timeout=30,
    )
    response.raise_for_status()
    jobs: list[JobApplication] = []
    for item in response.json():
        categories = item.get("categories", {})
        jobs.append(
            JobApplication(
                title=item["text"],
                company=company,
                location=categories.get("location", ""),
                source="lever",
                job_url=item["hostedUrl"],
                application_url=item.get("applyUrl", item["hostedUrl"]),
                description=item.get("descriptionPlain", ""),
            )
        )
    return jobs
