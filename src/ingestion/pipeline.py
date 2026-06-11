from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from src.ingestion.db import get_session, init_db, insert_dead_letters, upsert_bronze_jobs
from src.ingestion.fetcher import (
    fetch_all_sources,
    fetch_from_kaggle_fallback,
    fetch_from_remotive_api,
)
from src.ingestion.models import JobRecord
from src.logger import logger

Fetcher = Callable[[], list[dict[str, Any]]]


def _validate_jobs(
    raw_jobs: list[dict[str, Any]],
    source: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Validate raw job dicts against the JobRecord schema.

    Args:
        raw_jobs: Raw job dictionaries from the source.
        source: Source identifier string (e.g. ``"remotive"`` or ``"kaggle"``).

    Returns:
        A 2-tuple of ``(valid_jobs, dead_letters)`` — both as plain dicts ready
        for database persistence.
    """
    valid_jobs: list[dict[str, Any]] = []
    dead_letters: list[dict[str, Any]] = []

    for raw_job in raw_jobs:
        candidate = dict(raw_job)
        candidate.setdefault("source", source)
        try:
            record = JobRecord(**candidate)
            valid_jobs.append(record.to_bronze_dict())
        except ValidationError as exc:
            dead_letters.append(
                {
                    "source": source,
                    "raw_data": candidate,
                    "error_message": exc.errors(include_url=False)[0]["msg"],
                }
            )

    return valid_jobs, dead_letters


def _resolve_fetcher(source: str) -> tuple[str, Fetcher]:
    if source == "kaggle":
        return "kaggle", fetch_from_kaggle_fallback
    if source == "all":
        return "all", fetch_all_sources
    return "remotive", fetch_from_remotive_api


def run_ingestion(source: str = "remotive", db_url: str | None = None) -> dict[str, Any]:
    """Run the full ingestion pipeline: fetch → validate → persist.

    Writes validated records to the bronze layer and invalid records to the
    dead-letter table. Falls back to the Kaggle dataset when the Remotive API
    is unavailable.

    Args:
        source: Primary source identifier — ``"remotive"`` or ``"kaggle"``.
        db_url: Optional SQLAlchemy-compatible database URL override.

    Returns:
        A summary dict with keys: ``status``, ``source``, ``fetched``,
        ``valid``, ``invalid``.
    """
    logger.info("Starting ingestion pipeline  source=%s", source)
    init_db(db_url=db_url)

    active_source, fetcher = _resolve_fetcher(source)
    try:
        raw_jobs = fetcher()
    except Exception as exc:
        if active_source != "remotive":
            logger.exception("Primary source %s failed with no fallback.", active_source)
            return {"status": "error", "error": str(exc)}
        logger.warning("Remotive fetch failed — activating Kaggle fallback: %s", exc)
        active_source = "kaggle"
        raw_jobs = fetch_from_kaggle_fallback()

    valid_jobs, dead_letters = _validate_jobs(raw_jobs, active_source)

    session = get_session(db_url=db_url)
    try:
        stored_valid = upsert_bronze_jobs(session, valid_jobs)
        stored_invalid = insert_dead_letters(session, dead_letters)
    except Exception as exc:
        session.rollback()
        logger.exception("Ingestion database write failed.")
        return {"status": "error", "error": str(exc)}
    finally:
        session.close()

    summary: dict[str, Any] = {
        "status": "success",
        "source": active_source,
        "fetched": len(raw_jobs),
        "valid": stored_valid,
        "invalid": stored_invalid,
    }

    # Structured summary block — useful for log aggregation
    logger.info(
        "Ingestion complete | source=%-8s fetched=%4d  valid=%4d  invalid=%4d",
        active_source,
        summary["fetched"],
        summary["valid"],
        summary["invalid"],
    )
    return summary
