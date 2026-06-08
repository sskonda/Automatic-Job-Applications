from __future__ import annotations

from app.models import JobApplication


def import_email_alert(
    *,
    title: str,
    company: str,
    job_url: str,
    description: str,
    location: str = "",
    source: str = "email_alert",
) -> JobApplication:
    return JobApplication(
        title=title,
        company=company,
        location=location,
        source=source,
        job_url=job_url,
        application_url=job_url,
        description=description,
    )
