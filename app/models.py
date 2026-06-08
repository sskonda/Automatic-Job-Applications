from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ApplicationStatus(str, Enum):
    DISCOVERED = "discovered"
    RANKED = "ranked"
    MATERIALS_GENERATED = "materials_generated"
    QUEUED_FOR_SUBMISSION = "queued_for_submission"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    SPECIAL_CASE_WAITING_FOR_USER = "special_case_waiting_for_user"
    USER_REPLIED = "user_replied"
    RESUMED = "resumed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ARCHIVED = "archived"


class AuditEntry(BaseModel):
    timestamp: datetime = Field(default_factory=utc_now)
    action: str
    details: dict[str, Any] = Field(default_factory=dict)


class GeneratedMaterials(BaseModel):
    resume_path: str | None = None
    cover_letter: str | None = None
    short_answers: dict[str, str] = Field(default_factory=dict)


class JobApplication(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    company: str
    location: str = ""
    source: str
    job_url: str
    application_url: str | None = None
    description: str = ""
    score: float = 0.0
    recommendation: str = ""
    status: ApplicationStatus = ApplicationStatus.DISCOVERED
    source_allowlisted: bool = False
    auto_submit_allowed: bool = False
    matched_keywords: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    generated_materials: GeneratedMaterials = Field(default_factory=GeneratedMaterials)
    submitted_answers: dict[str, Any] = Field(default_factory=dict)
    submission_receipt: dict[str, Any] = Field(default_factory=dict)
    exception_reason: str | None = None
    exception_email_thread_id: str | None = None
    user_reply_instruction: str | None = None
    audit_log: list[AuditEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def log(self, action: str, **details: Any) -> None:
        self.audit_log.append(AuditEntry(action=action, details=details))
        self.updated_at = utc_now()

    def transition(self, status: ApplicationStatus, reason: str | None = None) -> None:
        previous = self.status
        self.status = status
        self.updated_at = utc_now()
        details: dict[str, Any] = {"from": previous.value, "to": status.value}
        if reason:
            details["reason"] = reason
        self.log("status_changed", **details)


class ApplicationIssue(BaseModel):
    category: str
    reason: str
    field_or_blocker: str
    options: list[str] = Field(default_factory=list)


class SubmissionResult(BaseModel):
    submitted: bool = False
    special_case: bool = False
    reason: str | None = None
    receipt: dict[str, Any] = Field(default_factory=dict)
