from __future__ import annotations

from collections.abc import Iterable
from datetime import date
import os
from pathlib import Path
import re
from typing import Any

import yaml

from app.application_submitter import ApplicationSubmitter
from app.config import Settings
from app.email_client import (
    EmailClient,
    attach_reply_to_job,
    resume_application_with_instruction,
)
from app.materials import generate_materials
from app.models import ApplicationStatus, JobApplication
from app.ranker import score_job
from app.storage import JobStore


def load_preapproved_answers(path: str | Path) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}

    def expand(value: Any) -> Any:
        if isinstance(value, str):
            match = re.fullmatch(r"\$\{([A-Z0-9_]+)\}", value.strip())
            return os.getenv(match.group(1), "") if match else value
        if isinstance(value, list):
            return [expand(item) for item in value]
        return value

    return {
        str(key).strip().lower(): expand(value)
        for key, value in data.items()
    }


def write_daily_report(
    jobs: Iterable[JobApplication],
    output_dir: str | Path,
    *,
    jobs_found: int,
    duplicates: int = 0,
    emails_sent: int = 0,
    replies_received: int = 0,
    report_date: date | None = None,
) -> Path:
    job_list = list(jobs)
    report_date = report_date or date.today()
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    report_path = output_path / f"daily_report_{report_date.isoformat()}.md"
    skipped = [job for job in job_list if job.status == ApplicationStatus.SKIPPED]
    submitted = [job for job in job_list if job.status == ApplicationStatus.SUBMITTED]
    paused = [
        job
        for job in job_list
        if job.status == ApplicationStatus.SPECIAL_CASE_WAITING_FOR_USER
    ]
    queued = [job for job in job_list if job.status == ApplicationStatus.QUEUED_FOR_SUBMISSION]

    def rows(items: list[JobApplication]) -> str:
        if not items:
            return "- None"
        return "\n".join(
            f"- {job.company} - {job.title} ({job.score:.1f}): {job.job_url}"
            for job in items
        )

    report_path.write_text(
        "\n".join(
            [
                f"# Daily Job Agent Report - {report_date.isoformat()}",
                "",
                "## Summary",
                f"- Jobs found: {jobs_found}",
                f"- Duplicates ignored: {duplicates}",
                f"- Jobs skipped: {len(skipped)}",
                f"- Applications queued: {len(queued)}",
                f"- Applications submitted: {len(submitted)}",
                f"- Applications paused for special cases: {len(paused)}",
                f"- Emails sent: {emails_sent}",
                f"- Replies received: {replies_received}",
                "",
                "## Submitted",
                rows(submitted),
                "",
                "## Special Cases",
                rows(paused),
                "",
                "## Skipped",
                rows(skipped),
                "",
                "## Next Actions",
                "- Review special-case emails and reply with approved instructions.",
                "- Review queued applications before enabling live auto-submit.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return report_path


class ApplicationQueue:
    def __init__(self, config: Settings, store: JobStore | None = None) -> None:
        self.config = config
        self.store = store or JobStore(config.database_path)
        self.email_client = EmailClient(config)
        self.submitter = ApplicationSubmitter(
            config, exception_handler=self.email_client.send_exception_email
        )

    def run(
        self,
        discovered_jobs: list[JobApplication],
        required_fields_by_job: dict[str, list[str]] | None = None,
    ) -> Path:
        imported, duplicates = self.store.import_jobs(discovered_jobs)
        answers = load_preapproved_answers(self.config.answers_path)
        emails_sent = 0
        for job in imported:
            score_job(job)
            if job.score < self.config.score_threshold:
                job.transition(ApplicationStatus.SKIPPED, "score below threshold")
                job.log("job_skipped", score=job.score, threshold=self.config.score_threshold)
                self.store.save(job)
                continue
            generate_materials(job, self.config)
            result = self.submitter.submit(
                job,
                (required_fields_by_job or {}).get(job.id, []),
                answers,
            )
            if result.special_case and job.exception_email_thread_id:
                emails_sent += 1
            self.store.save(job)
        return write_daily_report(
            imported,
            self.config.output_dir,
            jobs_found=len(discovered_jobs),
            duplicates=duplicates,
            emails_sent=emails_sent,
        )

    def process_email_replies(self) -> int:
        replies = self.email_client.poll_for_replies(self.store.waiting_thread_ids())
        processed = 0
        for reply in replies:
            job = self.store.get_by_thread_id(reply["thread_id"])
            if not job:
                continue
            attach_reply_to_job(job, reply["body"], self.store)
            resume_application_with_instruction(job, store=self.store)
            processed += 1
        return processed
