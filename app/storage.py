from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, Session, SQLModel, create_engine, select

from app.models import ApplicationStatus, JobApplication


class JobRecord(SQLModel, table=True):
    id: str = Field(primary_key=True)
    company: str
    title: str
    job_url: str = Field(index=True, unique=True)
    status: str = Field(index=True)
    score: float
    payload: str
    updated_at: str = Field(index=True)


class JobStore:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{self.database_path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        self._initialize()

    def _initialize(self) -> None:
        SQLModel.metadata.create_all(self.engine)

    def save(self, job: JobApplication) -> JobApplication:
        record = JobRecord(
            id=job.id,
            company=job.company,
            title=job.title,
            job_url=job.job_url,
            status=job.status.value,
            score=job.score,
            payload=job.model_dump_json(),
            updated_at=job.updated_at.isoformat(),
        )
        with Session(self.engine) as session:
            existing = session.get(JobRecord, job.id)
            if existing:
                for key, value in record.model_dump().items():
                    setattr(existing, key, value)
            else:
                session.add(record)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                duplicate = session.exec(
                    select(JobRecord).where(JobRecord.job_url == job.job_url)
                ).first()
                if duplicate and duplicate.id != job.id:
                    raise ValueError(f"A job with URL {job.job_url!r} already exists") from None
                raise
        return job

    def get(self, job_id: str) -> JobApplication | None:
        with Session(self.engine) as session:
            record = session.get(JobRecord, job_id)
        return JobApplication.model_validate_json(record.payload) if record else None

    def get_by_url(self, job_url: str) -> JobApplication | None:
        with Session(self.engine) as session:
            record = session.exec(
                select(JobRecord).where(JobRecord.job_url == job_url)
            ).first()
        return JobApplication.model_validate_json(record.payload) if record else None

    def list(self, status: str | None = None) -> list[JobApplication]:
        statement = select(JobRecord)
        if status:
            statement = statement.where(JobRecord.status == status)
        statement = statement.order_by(JobRecord.updated_at.desc())
        with Session(self.engine) as session:
            records = session.exec(statement).all()
        return [JobApplication.model_validate_json(record.payload) for record in records]

    def waiting_thread_ids(self) -> set[str]:
        return {
            job.exception_email_thread_id
            for job in self.list(ApplicationStatus.SPECIAL_CASE_WAITING_FOR_USER.value)
            if job.exception_email_thread_id
        }

    def get_by_thread_id(self, thread_id: str) -> JobApplication | None:
        for job in self.list(ApplicationStatus.SPECIAL_CASE_WAITING_FOR_USER.value):
            if job.exception_email_thread_id == thread_id:
                return job
        return None

    def import_jobs(self, jobs: list[JobApplication]) -> tuple[list[JobApplication], int]:
        saved: list[JobApplication] = []
        duplicates = 0
        for job in jobs:
            if self.get_by_url(job.job_url):
                duplicates += 1
                continue
            job.log("job_discovered", source=job.source, url=job.job_url)
            saved.append(self.save(job))
        return saved, duplicates

    def export_json(self, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps([job.model_dump(mode="json") for job in self.list()], indent=2),
            encoding="utf-8",
        )
