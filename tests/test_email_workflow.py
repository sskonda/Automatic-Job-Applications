from email import policy
from email.parser import BytesParser
from pathlib import Path

from app.config import Settings
from app.email_client import (
    EmailClient,
    attach_reply_to_job,
    build_exception_email,
    parse_reply_instruction,
    resume_application_with_instruction,
)
from app.models import ApplicationIssue, ApplicationStatus, JobApplication


def make_job() -> JobApplication:
    return JobApplication(
        title="RTL Design Engineer",
        company="Acme",
        source="greenhouse",
        job_url="https://boards.greenhouse.io/acme/jobs/123",
        score=91,
    )


def test_exception_email_is_generated_correctly() -> None:
    job = make_job()
    job.status = ApplicationStatus.SPECIAL_CASE_WAITING_FOR_USER
    issue = ApplicationIssue(
        category="missing_answer",
        reason="Required answer is missing",
        field_or_blocker="phone",
        options=["Provide phone", "Skip application"],
    )
    message = build_exception_email(job, issue, "Provide the approved phone number.", "me@example.com")
    body = message.get_content()
    assert message["Subject"] == "[ACTION NEEDED] Job Agent: Acme - RTL Design Engineer"
    assert "Question/field/blocker: phone" in body
    assert "Reply to this email" in body


def test_email_client_writes_local_draft(tmp_path: Path) -> None:
    cfg = Settings(output_dir=tmp_path)
    issue = ApplicationIssue(category="captcha", reason="CAPTCHA appeared", field_or_blocker="CAPTCHA")
    thread_id = EmailClient(cfg).send_exception_email(make_job(), issue, "Complete it manually.")
    draft = tmp_path / "email_drafts" / f"{thread_id}.eml"
    parsed = BytesParser(policy=policy.default).parsebytes(draft.read_bytes())
    assert parsed["To"] == "sanat.konda4@gmail.com"


def test_reply_is_parsed_and_attached() -> None:
    body = "Use yes for this application.\n\nOn Mon, Example wrote:\n> old content"
    job = attach_reply_to_job(make_job(), body)
    assert parse_reply_instruction(body) == "Use yes for this application."
    assert job.user_reply_instruction == "Use yes for this application."
    assert job.status == ApplicationStatus.USER_REPLIED


def test_job_resumes_after_user_reply() -> None:
    job = make_job()
    job.exception_reason = "Missing phone"
    attach_reply_to_job(job, "Use 555-0100")
    resume_application_with_instruction(job)
    assert job.status == ApplicationStatus.RESUMED
    assert job.exception_reason is None
