from __future__ import annotations

from fastapi.testclient import TestClient
from src.ingestion.db import get_session
from src.ingestion.pipeline import run_ingestion
from src.serving.api.dependencies import get_db
from src.serving.api.main import app
from src.transformation.runner import run_transformations

SAMPLE_JOB = {
    "id": 77,
    "url": "https://example.com/job77",
    "title": "Machine Learning Engineer",
    "company_name": "AI Tech",
    "publication_date": "2026-06-10T12:00:00Z",
    "candidate_required_location": "Toronto, Canada",
    "tags": ["python", "ml"],
}


def _make_client(sqlite_db_url: str):  # type: ignore[return]
    """Build a FastAPI TestClient wired to an in-memory SQLite DB."""

    def override_get_db():
        session = get_session(sqlite_db_url)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_api_returns_gold_trends(sqlite_db_url: str, mocker) -> None:
    mocker.patch("src.ingestion.pipeline.fetch_from_remotive_api", return_value=[SAMPLE_JOB])
    run_ingestion(db_url=sqlite_db_url)
    run_transformations(db_url=sqlite_db_url)

    client = _make_client(sqlite_db_url)
    try:
        response = client.get("/api/v1/trends/countries")
        assert response.status_code == 200
        assert response.json()[0]["country"] == "Canada"
    finally:
        app.dependency_overrides.clear()


def test_api_stats_endpoint(sqlite_db_url: str, mocker) -> None:
    """Stats endpoint returns pipeline totals from the live DB."""
    mocker.patch("src.ingestion.pipeline.fetch_from_remotive_api", return_value=[SAMPLE_JOB])
    run_ingestion(db_url=sqlite_db_url)
    run_transformations(db_url=sqlite_db_url)

    client = _make_client(sqlite_db_url)
    try:
        response = client.get("/api/v1/stats")
        assert response.status_code == 200
        body = response.json()
        assert body["total_jobs"] == 1
        assert "remotive" in body["sources"]
        assert body["total_countries"] >= 1
        assert body["total_skills"] >= 1
    finally:
        app.dependency_overrides.clear()


def test_api_jobs_endpoint_pagination(sqlite_db_url: str, mocker) -> None:
    """Jobs endpoint returns paginated bronze records."""
    mocker.patch("src.ingestion.pipeline.fetch_from_remotive_api", return_value=[SAMPLE_JOB])
    run_ingestion(db_url=sqlite_db_url)

    client = _make_client(sqlite_db_url)
    try:
        response = client.get("/api/v1/jobs?page=1&page_size=10")
        assert response.status_code == 200
        jobs = response.json()
        assert len(jobs) == 1
        assert jobs[0]["title"] == "Machine Learning Engineer"
    finally:
        app.dependency_overrides.clear()


def test_api_trend_filter_by_country(sqlite_db_url: str, mocker) -> None:
    """Country filter query param narrows gold trend results correctly."""
    mocker.patch("src.ingestion.pipeline.fetch_from_remotive_api", return_value=[SAMPLE_JOB])
    run_ingestion(db_url=sqlite_db_url)
    run_transformations(db_url=sqlite_db_url)

    client = _make_client(sqlite_db_url)
    try:
        # Matching filter
        r = client.get("/api/v1/trends/countries?country=Canada")
        assert r.status_code == 200
        assert r.json()[0]["country"] == "Canada"

        # Non-matching filter → empty list (200, not 404)
        r2 = client.get("/api/v1/trends/countries?country=Atlantis")
        assert r2.status_code == 200
        assert r2.json() == []
    finally:
        app.dependency_overrides.clear()


def test_api_health(sqlite_db_url: str) -> None:
    """Health endpoint always returns ok."""
    client = _make_client(sqlite_db_url)
    try:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    finally:
        app.dependency_overrides.clear()


def test_api_database_endpoints(sqlite_db_url: str, mocker) -> None:
    """Database inspector endpoints return table schemas and paginated data."""
    mocker.patch("src.ingestion.pipeline.fetch_from_remotive_api", return_value=[SAMPLE_JOB])
    run_ingestion(db_url=sqlite_db_url)
    run_transformations(db_url=sqlite_db_url)

    client = _make_client(sqlite_db_url)
    try:
        # 1. Test /api/v1/database/tables list
        r = client.get("/api/v1/database/tables")
        assert r.status_code == 200
        tables = r.json()
        assert "bronze_jobs" in tables
        assert "silver_jobs" in tables
        assert tables["bronze_jobs"]["row_count"] == 1
        
        # Verify columns schema
        cols = [c["name"] for c in tables["bronze_jobs"]["columns"]]
        assert "id" in cols
        assert "title" in cols
        assert "source" in cols

        # 2. Test /api/v1/database/table/{table_name} query
        r2 = client.get("/api/v1/database/table/bronze_jobs?page=1&page_size=10")
        assert r2.status_code == 200
        body = r2.json()
        assert body["table_name"] == "bronze_jobs"
        assert body["total_rows"] == 1
        assert len(body["rows"]) == 1
        assert body["rows"][0]["title"] == "Machine Learning Engineer"

        # 3. Test non-existent table returns 404
        r3 = client.get("/api/v1/database/table/non_existent_table")
        assert r3.status_code == 404
    finally:
        app.dependency_overrides.clear()

