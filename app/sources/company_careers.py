from __future__ import annotations

from app.models import JobApplication


def import_allowlisted_posting(
    *,
    title: str,
    company: str,
    job_url: str,
    application_url: str,
    description: str,
    location: str = "",
) -> JobApplication:
    return JobApplication(
        title=title,
        company=company,
        location=location,
        source="company_careers",
        job_url=job_url,
        application_url=application_url,
        description=description,
    )
