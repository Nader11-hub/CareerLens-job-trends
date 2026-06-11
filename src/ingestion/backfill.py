from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from src.ingestion.db import (
    fetch_unresolved_dead_letters,
    get_session,
    increment_dead_letter_retries,
    init_db,
    mark_dead_letters_resolved,
    upsert_bronze_jobs,
)
from src.ingestion.models import JobRecord
from src.logger import logger


def _sanitize_raw_job(raw_job: dict[str, Any]) -> dict[str, Any]:
    """Apply a small set of repair rules before retrying validation."""

    cleaned = dict(raw_job)
    url = cleaned.get("url")
    if isinstance(url, str) and url and not url.startswith(("http://", "https://")):
        cleaned["url"] = f"https://{url.lstrip('/')}"
    return cleaned


def run_dead_letter_backfill(db_url: str | None = None, limit: int = 100) -> dict[str, int]:
    """Retry unresolved dead-letter rows and move recoverable rows into bronze."""

    init_db(db_url=db_url)
    session = get_session(db_url=db_url)
    retried = succeeded = failed = 0

    try:
        dead_letters = fetch_unresolved_dead_letters(session, limit=limit)
        retried = len(dead_letters)

        success_ids: list[int] = []
        retry_ids: list[int] = []
        recovered_jobs: list[dict[str, Any]] = []

        for dead_letter in dead_letters:
            payload = _sanitize_raw_job(dead_letter.raw_data)
            payload.setdefault("source", dead_letter.source)
            try:
                record = JobRecord(**payload)
                recovered_jobs.append(record.to_bronze_dict())
                success_ids.append(dead_letter.id)
            except ValidationError:
                retry_ids.append(dead_letter.id)

        if recovered_jobs:
            upsert_bronze_jobs(session, recovered_jobs)
            succeeded = mark_dead_letters_resolved(session, success_ids)
        if retry_ids:
            failed = increment_dead_letter_retries(session, retry_ids)
    finally:
        session.close()

    result = {"retried": retried, "recovered": succeeded, "failed": failed}
    logger.info("Dead-letter backfill completed: %s", result)
    return result
