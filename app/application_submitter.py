from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urlparse

from app.config import Settings
from app.models import (
    ApplicationIssue,
    ApplicationStatus,
    JobApplication,
    SubmissionResult,
)


PLATFORM_ALLOWLIST = {"greenhouse", "lever", "ashby"}
BLOCKED_PLATFORMS = {"linkedin", "indeed"}
SENSITIVE_FIELDS = {
    "work authorization",
    "visa sponsorship",
    "sponsorship",
    "citizenship",
    "security clearance",
    "disability",
    "veteran status",
    "eeo",
    "salary expectations",
    "relocation",
    "background check consent",
    "legal consent",
    "references",
    "government id",
    "social security number",
    "ssn",
    "date of birth",
    "protected demographic",
}


def source_policy(job: JobApplication, config: Settings) -> tuple[bool, str]:
    source = job.source.strip().lower()
    url = (job.application_url or job.job_url).lower()
    if source in BLOCKED_PLATFORMS or "linkedin.com" in url or "indeed.com" in url:
        return False, "LinkedIn and Indeed applications require manual review"
    if source in PLATFORM_ALLOWLIST:
        return True, ""
    hostname = (urlparse(url).hostname or "").lower()
    if hostname in config.allowed_company_domains:
        return True, ""
    return False, "source is not allowlisted"


def detect_sensitive_field(field_name: str) -> str | None:
    normalized = field_name.strip().lower()
    return next((term for term in SENSITIVE_FIELDS if term in normalized), None)


def validate_required_answers(
    required_fields: list[str], preapproved_answers: dict[str, object]
) -> ApplicationIssue | None:
    normalized_answers = {key.strip().lower(): value for key, value in preapproved_answers.items()}
    for field_name in required_fields:
        key = field_name.strip().lower()
        sensitive_match = detect_sensitive_field(field_name)
        value = normalized_answers.get(key)
        if sensitive_match and value in (None, "", []):
            return ApplicationIssue(
                category="sensitive_field",
                reason="A sensitive or legal answer has not been pre-approved",
                field_or_blocker=field_name,
            )
        if value in (None, "", []):
            return ApplicationIssue(
                category="missing_answer",
                reason="A required answer is missing from preapproved_answers.yaml",
                field_or_blocker=field_name,
            )
    return None


class ApplicationSubmitter:
    def __init__(
        self,
        config: Settings,
        exception_handler: Callable[[JobApplication, ApplicationIssue, str], str] | None = None,
    ) -> None:
        self.config = config
        self.exception_handler = exception_handler

    def _special_case(
        self, job: JobApplication, issue: ApplicationIssue, recommendation: str
    ) -> SubmissionResult:
        job.exception_reason = f"{issue.reason}: {issue.field_or_blocker}"
        job.auto_submit_allowed = False
        job.transition(ApplicationStatus.SPECIAL_CASE_WAITING_FOR_USER, job.exception_reason)
        job.log(
            "special_case_created",
            category=issue.category,
            blocker=issue.field_or_blocker,
            recommendation=recommendation,
        )
        if self.exception_handler:
            job.exception_email_thread_id = self.exception_handler(job, issue, recommendation)
            job.log("exception_email_sent", thread_id=job.exception_email_thread_id)
        return SubmissionResult(special_case=True, reason=job.exception_reason)

    def submit(
        self,
        job: JobApplication,
        required_fields: list[str],
        preapproved_answers: dict[str, object],
        *,
        captcha_present: bool = False,
        adapter: Callable[[JobApplication, dict[str, object]], dict[str, object]] | None = None,
    ) -> SubmissionResult:
        allowed, reason = source_policy(job, self.config)
        job.source_allowlisted = allowed
        if not allowed:
            return self._special_case(
                job,
                ApplicationIssue(
                    category="source_policy",
                    reason=reason,
                    field_or_blocker=job.application_url or job.job_url,
                ),
                "Review and complete this application manually.",
            )
        if captcha_present:
            return self._special_case(
                job,
                ApplicationIssue(
                    category="captcha",
                    reason="CAPTCHA or anti-bot challenge appeared",
                    field_or_blocker="CAPTCHA",
                ),
                "Complete the challenge manually, then reply when the session is ready.",
            )
        issue = validate_required_answers(required_fields, preapproved_answers)
        if issue:
            return self._special_case(
                job,
                issue,
                "Reply with the exact answer you want saved and used for this application.",
            )
        if job.score < self.config.score_threshold:
            job.transition(ApplicationStatus.SKIPPED, "score below auto-submit threshold")
            job.log("submission_skipped", score=job.score, threshold=self.config.score_threshold)
            return SubmissionResult(reason="score below auto-submit threshold")
        if not self.config.auto_submit_enabled:
            job.auto_submit_allowed = True
            job.transition(ApplicationStatus.QUEUED_FOR_SUBMISSION)
            job.log("submission_queued", dry_run=True)
            return SubmissionResult(reason="auto-submit is disabled; application queued")
        if adapter is None:
            return self._special_case(
                job,
                ApplicationIssue(
                    category="unsupported_workflow",
                    reason="No approved portal adapter is configured",
                    field_or_blocker=job.source,
                ),
                "Review the portal and add or approve a supported adapter.",
            )

        job.auto_submit_allowed = True
        job.transition(ApplicationStatus.SUBMITTING)
        normalized_answers = {
            key.strip().lower(): value for key, value in preapproved_answers.items()
        }
        answers = {field: normalized_answers[field.strip().lower()] for field in required_fields}
        for field, value in answers.items():
            job.submitted_answers[field] = value
            job.log("field_filled", field=field, value=value)
        receipt = adapter(job, answers)
        job.submission_receipt = receipt
        job.transition(ApplicationStatus.SUBMITTED)
        job.log("application_submitted", receipt=receipt)
        return SubmissionResult(submitted=True, receipt=receipt)
