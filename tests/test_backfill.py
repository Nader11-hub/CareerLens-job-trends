from __future__ import annotations

from src.ingestion.backfill import run_dead_letter_backfill
from src.ingestion.db import BronzeJob, BronzeJobDeadLetter, get_session, init_db


def test_dead_letter_backfill_recovers_fixable_url(sqlite_db_url: str) -> None:
    init_db(db_url=sqlite_db_url)
    session = get_session(sqlite_db_url)
    session.add(
        BronzeJobDeadLetter(
            source="kaggle",
            raw_data={
                "id": 99,
                "url": "example.com/job/99",
                "title": "Data Analyst",
                "company_name": "CareerLens",
                "publication_date": "2026-06-10T12:00:00Z",
            },
            error_message="URL must start with http:// or https://",
        )
    )
    session.commit()
    session.close()

    result = run_dead_letter_backfill(db_url=sqlite_db_url)

    assert result["recovered"] == 1

    session = get_session(sqlite_db_url)
    try:
        assert session.query(BronzeJob).count() == 1
        recovered_row = session.query(BronzeJobDeadLetter).first()
        assert recovered_row is not None
        assert recovered_row.resolved is True
    finally:
        session.close()
