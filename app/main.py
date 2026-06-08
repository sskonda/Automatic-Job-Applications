from __future__ import annotations

from fastapi import FastAPI, HTTPException

from app.config import settings
from app.models import JobApplication
from app.ranker import score_job
from app.storage import JobStore


app = FastAPI(title="Sanat's Local Job Application Agent", version="0.1.0")
store = JobStore(settings.database_path)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/jobs", response_model=list[JobApplication])
def list_jobs(status: str | None = None) -> list[JobApplication]:
    return store.list(status)


@app.get("/jobs/{job_id}", response_model=JobApplication)
def get_job(job_id: str) -> JobApplication:
    job = store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/jobs", response_model=JobApplication)
def create_job(job: JobApplication) -> JobApplication:
    existing = store.get_by_url(job.job_url)
    if existing:
        return existing
    job.log("job_discovered", source=job.source, url=job.job_url)
    score_job(job)
    return store.save(job)
