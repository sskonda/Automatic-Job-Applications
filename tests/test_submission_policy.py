from pathlib import Path

from app.application_submitter import ApplicationSubmitter, source_policy
from app.config import Settings
from app.email_client import EmailClient
from app.models import ApplicationStatus, JobApplication


def make_job(source: str, url: str, score: float = 90) -> JobApplication:
    return JobApplication(
        title="FPGA Engineer",
        company="Example",
        source=source,
        job_url=url,
        application_url=url,
        score=score,
    )


def config(tmp_path: Path, auto_submit: bool = False) -> Settings:
    return Settings(
        database_path=tmp_path / "jobs.db",
        output_dir=tmp_path / "outputs",
        answers_path=tmp_path / "answers.yaml",
        auto_submit_enabled=auto_submit,
    )


def test_linkedin_url_auto_submit_blocked(tmp_path: Path) -> None:
    allowed, reason = source_policy(
        make_job("manual", "https://linkedin.com/jobs/view/123"), config(tmp_path)
    )
    assert not allowed
    assert "manual review" in reason


def test_indeed_url_auto_submit_blocked(tmp_path: Path) -> None:
    allowed, reason = source_policy(
        make_job("email_alert", "https://indeed.com/viewjob?jk=123"), config(tmp_path)
    )
    assert not allowed
    assert "manual review" in reason


def test_sensitive_field_triggers_special_case(tmp_path: Path) -> None:
    job = make_job("greenhouse", "https://boards.greenhouse.io/example/jobs/123")
    result = ApplicationSubmitter(config(tmp_path)).submit(
        job, ["work authorization"], {}
    )
    assert result.special_case
    assert job.status == ApplicationStatus.SPECIAL_CASE_WAITING_FOR_USER


def test_missing_answer_triggers_email(tmp_path: Path) -> None:
    cfg = config(tmp_path)
    email = EmailClient(cfg, draft_dir=tmp_path / "drafts")
    submitter = ApplicationSubmitter(cfg, exception_handler=email.send_exception_email)
    job = make_job("lever", "https://jobs.lever.co/example/123")
    result = submitter.submit(job, ["phone"], {})
    assert result.special_case
    assert job.exception_email_thread_id
    assert list((tmp_path / "drafts").glob("*.eml"))


def test_auto_submit_only_happens_for_allowlisted_source(tmp_path: Path) -> None:
    cfg = config(tmp_path, auto_submit=True)
    submitter = ApplicationSubmitter(cfg)
    blocked = make_job("company_careers", "https://unknown.example/jobs/123")
    result = submitter.submit(blocked, [], {}, adapter=lambda *_: {"id": "no"})
    assert not result.submitted
    assert result.special_case


def test_submission_audit_records_steps(tmp_path: Path) -> None:
    cfg = config(tmp_path, auto_submit=True)
    job = make_job("greenhouse", "https://boards.greenhouse.io/example/jobs/123")
    result = ApplicationSubmitter(cfg).submit(
        job,
        ["name"],
        {"name": "Sanat Konda"},
        adapter=lambda _job, _answers: {"confirmation": "ABC-123"},
    )
    actions = [entry.action for entry in job.audit_log]
    assert result.submitted
    assert "field_filled" in actions
    assert "application_submitted" in actions
    assert job.submission_receipt["confirmation"] == "ABC-123"


def test_captcha_is_never_bypassed(tmp_path: Path) -> None:
    job = make_job("ashby", "https://jobs.ashbyhq.com/example/123")
    result = ApplicationSubmitter(config(tmp_path, auto_submit=True)).submit(
        job, [], {}, captcha_present=True, adapter=lambda *_: {"id": "should-not-run"}
    )
    assert result.special_case
    assert not result.submitted
    assert "CAPTCHA" in (job.exception_reason or "")
