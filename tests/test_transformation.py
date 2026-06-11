from __future__ import annotations

from src.ingestion.db import GoldCountryTrend, GoldSkillTrend, GoldTimeTrend, SilverJob, get_session
from src.ingestion.pipeline import run_ingestion
from src.transformation.runner import run_transformations

SAMPLE_JOBS = [
    {
        "id": 1,
        "url": "https://example.com/job1",
        "title": "Data Engineer",
        "company_name": "Tech Giants",
        "publication_date": "2026-06-01T10:00:00Z",
        "candidate_required_location": "Remote, USA",
        "tags": ["python", "sql"],
    },
    {
        "id": 2,
        "url": "https://example.com/job2",
        "title": "Analytics Engineer",
        "company_name": "Insight Labs",
        "publication_date": "2026-06-02T10:00:00Z",
        "candidate_required_location": "Worldwide",
        "tags": ["dbt", "sql"],
    },
]


def test_transformation_builds_silver_and_gold(sqlite_db_url: str, mocker) -> None:
    mocker.patch("src.ingestion.pipeline.fetch_from_remotive_api", return_value=SAMPLE_JOBS)
    run_ingestion(db_url=sqlite_db_url)

    result = run_transformations(db_url=sqlite_db_url)

    assert result["silver_jobs"] == 2

    session = get_session(sqlite_db_url)
    try:
        assert session.query(SilverJob).count() == 2
        assert session.query(GoldCountryTrend).count() >= 2
        assert session.query(GoldSkillTrend).count() >= 3
        assert session.query(GoldTimeTrend).count() == 1
    finally:
        session.close()
