from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from src.ingestion.db import BronzeJob, BronzeJobDeadLetter, get_session
from src.ingestion.models import JobRecord
from src.ingestion.pipeline import run_ingestion

VALID_JOB = {
    "id": 12345,
    "url": "https://remotive.com/jobs/12345",
    "title": "Data Engineer",
    "company_name": "TestCorp",
    "publication_date": "2026-06-10T12:00:00Z",
    "tags": ["python", "sql"],
    "category": "Software",
    "job_type": "full_time",
}

INVALID_JOB_URL = {
    "id": 12346,
    "url": "invalid-url",
    "title": "Software Engineer",
    "company_name": "TestCorp",
    "publication_date": "2026-06-10T12:00:00Z",
}


def test_job_record_validation() -> None:
    record = JobRecord(**VALID_JOB)
    assert record.id == 12345
    assert record.publication_date == datetime(2026, 6, 10, 12, 0, tzinfo=UTC)

    with pytest.raises(ValidationError):
        JobRecord(**INVALID_JOB_URL)


def test_ingestion_pipeline_with_sqlite(sqlite_db_url: str, mocker: pytest.MonkeyPatch) -> None:
    mock_jobs = [VALID_JOB, INVALID_JOB_URL]
    mocker.patch("src.ingestion.pipeline.fetch_from_remotive_api", return_value=mock_jobs)

    result = run_ingestion(source="remotive", db_url=sqlite_db_url)

    assert result["status"] == "success"
    assert result["fetched"] == 2
    assert result["valid"] == 1
    assert result["invalid"] == 1

    session = get_session(sqlite_db_url)
    try:
        assert session.query(BronzeJob).count() == 1
        assert session.query(BronzeJobDeadLetter).count() == 1
    finally:
        session.close()


def test_ingestion_pipeline_fallback(sqlite_db_url: str, mocker: pytest.MonkeyPatch) -> None:
    mocker.patch(
        "src.ingestion.pipeline.fetch_from_remotive_api",
        side_effect=Exception("API Down"),
    )
    mocker.patch("src.ingestion.pipeline.fetch_from_kaggle_fallback", return_value=[VALID_JOB])

    result = run_ingestion(source="remotive", db_url=sqlite_db_url)

    assert result["status"] == "success"
    assert result["source"] == "kaggle"
    assert result["valid"] == 1
