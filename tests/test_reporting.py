from datetime import date
from pathlib import Path

from app.application_queue import write_daily_report
from app.models import ApplicationStatus, JobApplication


def test_daily_report_is_created(tmp_path: Path) -> None:
    job = JobApplication(
        title="FPGA Engineer",
        company="Acme",
        source="greenhouse",
        job_url="https://example.com/1",
        score=90,
        status=ApplicationStatus.SUBMITTED,
    )
    path = write_daily_report(
        [job],
        tmp_path,
        jobs_found=1,
        emails_sent=0,
        report_date=date(2026, 6, 7),
    )
    assert path.name == "daily_report_2026-06-07.md"
    assert "Applications submitted: 1" in path.read_text(encoding="utf-8")
