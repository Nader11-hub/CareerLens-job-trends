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


def test_fetch_from_jsearch_no_key(mocker: pytest.MonkeyPatch) -> None:
    # Verify it returns empty list if jsearch_api_key is empty
    mocker.patch("src.ingestion.fetcher.settings.jsearch_api_key", "")
    from src.ingestion.fetcher import fetch_from_jsearch
    assert fetch_from_jsearch() == []


def test_fetch_from_jsearch_success(mocker: pytest.MonkeyPatch) -> None:
    mocker.patch("src.ingestion.fetcher.settings.jsearch_api_key", "mocked-key")
    mocker.patch("src.ingestion.fetcher.settings.jsearch_api_url", "http://mock-url")

    mock_response = mocker.Mock()
    mock_response.json.return_value = {
        "data": [
            {
                "job_id": "xyz-123",
                "job_apply_link": "https://example.com/apply",
                "job_title": "Senior AI Architect",
                "employer_name": "DeepMind Partner",
                "employer_logo": "https://example.com/logo.png",
                "job_category": "Engineering",
                "job_posted_at_datetime_utc": "2026-06-11T12:00:00.000Z",
                "job_country": "US",
                "job_min_salary": 120000,
                "job_max_salary": 180000,
                "job_salary_currency": "USD",
                "job_description": "We are seeking a python/pytorch engineer...",
                "job_highlights": {
                    "Qualifications": [
                        "Must have 5+ years with python and pytorch",
                        "Experience with FastAPI or django",
                    ]
                }
            }
        ]
    }
    mock_response.raise_for_status = mocker.Mock()
    mocker.patch("requests.get", return_value=mock_response)

    from src.ingestion.fetcher import fetch_from_jsearch
    jobs = fetch_from_jsearch(num_pages=1)
    assert len(jobs) == 1
    job = jobs[0]
    assert job["company_name"] == "DeepMind Partner"
    assert job["title"] == "Senior AI Architect"
    assert job["source"] == "jsearch"
    # Verify the tokenized tags
    assert "python" in job["tags"]
    assert "pytorch" in job["tags"]
    assert "fastapi" in job["tags"]
    assert "django" in job["tags"]


def test_fetch_all_sources_incorporates_jsearch(mocker: pytest.MonkeyPatch) -> None:
    mocker.patch("src.ingestion.fetcher.settings.jsearch_api_key", "mocked-key")

    mock_remotive = [{"url": "http://x.com/r1", "id": 1, "source": "remotive"}]
    mock_remoteok = [{"url": "http://x.com/ro1", "id": 2, "source": "remoteok"}]
    mock_arbeitnow = [{"url": "http://x.com/an1", "id": 3, "source": "arbeitnow"}]
    mock_jsearch = [{"url": "http://x.com/js1", "id": 4, "source": "jsearch"}]

    mocker.patch("src.ingestion.fetcher.fetch_from_remotive_all_categories", return_value=mock_remotive)
    mocker.patch("src.ingestion.fetcher.fetch_from_remoteok", return_value=mock_remoteok)
    mocker.patch("src.ingestion.fetcher.fetch_from_arbeitnow", return_value=mock_arbeitnow)
    mocker.patch("src.ingestion.fetcher.fetch_from_jsearch", return_value=mock_jsearch)

    from src.ingestion.fetcher import fetch_all_sources
    res = fetch_all_sources()
    assert len(res) == 4
    sources = [r.get("source") for r in res]
    assert "remotive" in sources
    assert "remoteok" in sources
    assert "arbeitnow" in sources
    assert "jsearch" in sources


