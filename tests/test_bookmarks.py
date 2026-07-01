from __future__ import annotations

import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from src.ingestion.db import BookmarkedJob, get_session, init_db
from src.serving.api.main import app
from src.serving.api.service import (
    add_bookmark,
    get_bookmarks,
    remove_bookmark,
    update_bookmark_notes,
)


@pytest.fixture
def db_session(sqlite_db_url: str) -> Session:
    """Create in-memory SQLite session with tables initialized."""
    init_db(db_url=sqlite_db_url)
    session = get_session(db_url=sqlite_db_url)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def api_client(sqlite_db_url: str) -> TestClient:
    """Create a FastAPI test client configured with in-memory SQLite."""
    # Override dependencies
    from src.serving.api.dependencies import get_db
    init_db(db_url=sqlite_db_url)

    def override_get_db():
        session = get_session(db_url=sqlite_db_url)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_add_and_get_bookmarks(db_session: Session) -> None:
    # Initially empty
    assert len(get_bookmarks(db_session)) == 0

    # Add bookmarks
    b1 = add_bookmark(db_session, job_id=101, notes="First bookmark")
    b2 = add_bookmark(db_session, job_id=102, notes="Second bookmark")

    # Verify duplicate add returns existing
    b1_dup = add_bookmark(db_session, job_id=101, notes="Different notes")
    assert b1.id == b1_dup.id
    assert b1.notes == "First bookmark"

    # Get bookmarks (sorted by date desc)
    bookmarks = get_bookmarks(db_session)
    assert len(bookmarks) == 2
    assert bookmarks[0].job_id == 102
    assert bookmarks[1].job_id == 101


def test_remove_bookmark(db_session: Session) -> None:
    add_bookmark(db_session, job_id=101, notes="Remove me")
    assert len(get_bookmarks(db_session)) == 1

    # Remove successfully
    assert remove_bookmark(db_session, job_id=101) is True
    assert len(get_bookmarks(db_session)) == 0

    # Remove non-existent
    assert remove_bookmark(db_session, job_id=999) is False


def test_update_bookmark_notes(db_session: Session) -> None:
    add_bookmark(db_session, job_id=101, notes="Old notes")

    # Update successfully
    updated = update_bookmark_notes(db_session, job_id=101, notes="New notes")
    assert updated is not None
    assert updated.notes == "New notes"

    # Update non-existent
    assert update_bookmark_notes(db_session, job_id=999, notes="N/A") is None


def test_api_bookmarks_flow(api_client: TestClient) -> None:
    # 1. List bookmarks (empty)
    resp = api_client.get("/api/v1/bookmarks")
    assert resp.status_code == 200
    assert resp.json() == []

    # 2. Create a bookmark
    resp = api_client.post("/api/v1/bookmarks", json={"job_id": 401, "notes": "API test"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["job_id"] == 401
    assert data["notes"] == "API test"
    assert "id" in data

    # 3. List bookmarks (has 1 item)
    resp = api_client.get("/api/v1/bookmarks")
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["job_id"] == 401

    # 4. Update bookmark notes
    resp = api_client.put("/api/v1/bookmarks/401", json={"notes": "Updated API notes"})
    assert resp.status_code == 200
    assert resp.json()["notes"] == "Updated API notes"

    # 5. Delete bookmark
    resp = api_client.delete("/api/v1/bookmarks/401")
    assert resp.status_code == 200
    assert "removed successfully" in resp.json()["message"]

    # 6. List bookmarks (empty again)
    resp = api_client.get("/api/v1/bookmarks")
    assert resp.status_code == 200
    assert resp.json() == []

