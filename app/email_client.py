from __future__ import annotations

import base64
import re
from email.message import EmailMessage
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.config import Settings
from app.models import ApplicationIssue, ApplicationStatus, JobApplication
from app.storage import JobStore


def build_exception_email(
    job: JobApplication, issue: ApplicationIssue, recommendation: str, recipient: str
) -> EmailMessage:
    message = EmailMessage()
    message["To"] = recipient
    message["Subject"] = f"[ACTION NEEDED] Job Agent: {job.company} - {job.title}"
    options = "\n".join(f"- {option}" for option in issue.options) or "- None provided"
    message.set_content(
        "\n".join(
            [
                f"Company: {job.company}",
                f"Job title: {job.title}",
                f"Job URL: {job.job_url}",
                f"Fit score: {job.score:.1f}",
                f"Current application status: {job.status.value}",
                f"Exact reason the agent stopped: {issue.reason}",
                f"Question/field/blocker: {issue.field_or_blocker}",
                "Options available:",
                options,
                f"Recommended answer or action: {recommendation}",
                "",
                "Reply to this email with the answer or instruction you want the agent to use.",
            ]
        )
    )
    return message


class EmailClient:
    def __init__(self, config: Settings, draft_dir: str | Path | None = None) -> None:
        self.config = config
        self.draft_dir = Path(draft_dir or config.output_dir / "email_drafts")

    def _gmail_service(self) -> Any:
        if not (
            self.config.gmail_sender
            and self.config.gmail_credentials_path
            and self.config.gmail_token_path
        ):
            return None
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        scopes = ["https://www.googleapis.com/auth/gmail.modify"]
        token_path = Path(self.config.gmail_token_path)
        credentials = (
            Credentials.from_authorized_user_file(token_path, scopes) if token_path.exists() else None
        )
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        if not credentials or not credentials.valid:
            flow = InstalledAppFlow.from_client_secrets_file(
                self.config.gmail_credentials_path, scopes
            )
            credentials = flow.run_local_server(port=0)
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(credentials.to_json(), encoding="utf-8")
        return build("gmail", "v1", credentials=credentials)

    def send_exception_email(
        self, job: JobApplication, issue: ApplicationIssue, recommendation: str
    ) -> str:
        message = build_exception_email(job, issue, recommendation, self.config.gmail_recipient)
        if self.config.gmail_sender:
            message["From"] = self.config.gmail_sender
        service = self._gmail_service()
        if service:
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            response = (
                service.users()
                .messages()
                .send(userId="me", body={"raw": raw})
                .execute()
            )
            return response.get("threadId") or response["id"]

        self.draft_dir.mkdir(parents=True, exist_ok=True)
        local_id = f"local-{uuid4()}"
        (self.draft_dir / f"{local_id}.eml").write_bytes(message.as_bytes())
        return local_id

    def poll_for_replies(self, known_thread_ids: set[str] | None = None) -> list[dict[str, str]]:
        service = self._gmail_service()
        if not service:
            return []
        response = (
            service.users()
            .messages()
            .list(userId="me", q="is:unread subject:\"[ACTION NEEDED] Job Agent:\"")
            .execute()
        )
        replies: list[dict[str, str]] = []
        for item in response.get("messages", []):
            message = service.users().messages().get(userId="me", id=item["id"]).execute()
            thread_id = message.get("threadId", "")
            if known_thread_ids and thread_id not in known_thread_ids:
                continue
            payload = message.get("payload", {})
            body_data = payload.get("body", {}).get("data", "")
            if not body_data:
                for part in payload.get("parts", []):
                    if part.get("mimeType") == "text/plain":
                        body_data = part.get("body", {}).get("data", "")
                        break
            body = (
                base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")
                if body_data
                else ""
            )
            replies.append(
                {"message_id": item["id"], "thread_id": thread_id, "body": body}
            )
        return replies


def send_exception_email(
    job: JobApplication,
    issue: ApplicationIssue,
    recommendation: str,
    config: Settings,
) -> str:
    return EmailClient(config).send_exception_email(job, issue, recommendation)


def poll_for_replies(config: Settings, known_thread_ids: set[str] | None = None) -> list[dict[str, str]]:
    return EmailClient(config).poll_for_replies(known_thread_ids)


def parse_reply_instruction(body: str) -> str:
    lines: list[str] = []
    for line in body.replace("\r\n", "\n").split("\n"):
        stripped = line.strip()
        if stripped.startswith(">"):
            continue
        if re.match(r"^On .+ wrote:$", stripped):
            break
        if stripped == "--":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def attach_reply_to_job(
    job: JobApplication, reply_body: str, store: JobStore | None = None
) -> JobApplication:
    instruction = parse_reply_instruction(reply_body)
    job.user_reply_instruction = instruction
    job.transition(ApplicationStatus.USER_REPLIED)
    job.log("user_reply_received", instruction=instruction)
    if store:
        store.save(job)
    return job


def resume_application_with_instruction(
    job: JobApplication,
    instruction: str | None = None,
    store: JobStore | None = None,
) -> JobApplication:
    resolved_instruction = (instruction or job.user_reply_instruction or "").strip()
    if not resolved_instruction:
        raise ValueError("A reply instruction is required before resuming")
    job.user_reply_instruction = resolved_instruction
    job.exception_reason = None
    job.transition(ApplicationStatus.RESUMED)
    job.log("application_resumed", instruction=resolved_instruction)
    if store:
        store.save(job)
    return job
