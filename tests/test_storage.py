from pathlib import Path

from app.models import ApplicationStatus, JobApplication
from app.storage import JobStore


def test_sqlmodel_storage_round_trip_and_deduplication(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.db")
    job = JobApplication(
        title="FPGA Engineer",
        company="Acme",
        source="greenhouse",
        job_url="https://boards.greenhouse.io/acme/jobs/123",
        score=88,
        status=ApplicationStatus.RANKED,
    )
    saved, duplicates = store.import_jobs([job])
    loaded = store.get(job.id)
    _, duplicate_count = store.import_jobs([job])

    assert len(saved) == 1
    assert duplicates == 0
    assert loaded is not None
    assert loaded.title == "FPGA Engineer"
    assert duplicate_count == 1
