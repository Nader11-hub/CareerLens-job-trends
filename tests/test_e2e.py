from __future__ import annotations

from fastapi.testclient import TestClient
from src.ingestion.db import get_session
from src.orchestration.runner import run_pipeline
from src.serving.api.dependencies import get_db
from src.serving.api.main import app

SAMPLE_JOBS = [
    {
        "id": 201,
        "url": "https://example.com/201",
        "title": "Data Engineer",
        "company_name": "Northwind",
        "publication_date": "2026-06-01T12:00:00Z",
        "candidate_required_location": "Berlin, Germany",
        "tags": ["python", "sql"],
    },
    {
        "id": 202,
        "url": "https://example.com/202",
        "title": "Analytics Engineer",
        "company_name": "Northwind",
        "publication_date": "2026-06-15T12:00:00Z",
        "candidate_required_location": "Worldwide",
        "tags": ["dbt", "sql"],
    },
]


def test_end_to_end_pipeline(sqlite_db_url: str, mocker) -> None:
    mocker.patch("src.ingestion.pipeline.fetch_from_remotive_api", return_value=SAMPLE_JOBS)

    result = run_pipeline(source="remotive", db_url=sqlite_db_url, use_dbt=False)

    assert result["status"] == "success"
    assert result["ingestion"]["valid"] == 2
    assert result["transformation"]["silver_jobs"] == 2

    def override_get_db():
        session = get_session(sqlite_db_url)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    try:
        time_response = client.get("/api/v1/trends/time")
        role_response = client.get("/api/v1/trends/roles")
        assert time_response.status_code == 200
        assert role_response.status_code == 200
        assert len(time_response.json()) == 1
        assert len(role_response.json()) == 2
    finally:
        app.dependency_overrides.clear()
