"""Standalone CLI for the dead-letter backfill process.

Usage examples::

    # Run backfill against the default database:
    python -m src.ingestion.backfill_cli

    # Dry-run: show what would be recovered without writing:
    python -m src.ingestion.backfill_cli --dry-run

    # Custom DB and larger batch:
    python -m src.ingestion.backfill_cli --db-url sqlite:///local.db --limit 200
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

from pydantic import ValidationError

from src.ingestion.backfill import _sanitize_raw_job
from src.ingestion.db import fetch_unresolved_dead_letters, get_session, init_db
from src.ingestion.models import JobRecord
from src.logger import logger


def _dry_run(db_url: str | None, limit: int) -> dict[str, Any]:
    """Inspect dead-letter records without modifying the database.

    Args:
        db_url: Optional database URL override.
        limit: Maximum number of dead-letter records to inspect.

    Returns:
        A summary dict with ``retried``, ``recoverable``, ``unrecoverable`` counts.
    """
    init_db(db_url=db_url)
    session = get_session(db_url=db_url)
    recoverable = 0
    unrecoverable = 0

    try:
        dead_letters = fetch_unresolved_dead_letters(session, limit=limit)
        print(f"\n{'─' * 72}")
        print(f"  DRY-RUN — inspecting {len(dead_letters)} unresolved dead-letter records")
        print(f"{'─' * 72}")

        for dl in dead_letters:
            payload = _sanitize_raw_job(dl.raw_data)
            payload.setdefault("source", dl.source)
            try:
                JobRecord(**payload)
                recoverable += 1
                status = "✅ RECOVERABLE"
            except ValidationError as exc:
                unrecoverable += 1
                status = f"❌ STILL INVALID  ({exc.errors(include_url=False)[0]['msg']})"

            print(f"  [{dl.id:>4}] source={dl.source:<10}  retries={dl.retry_count}  {status}")

        print(f"{'─' * 72}")
        print(f"  Recoverable: {recoverable}   |   Still invalid: {unrecoverable}")
        print(f"{'─' * 72}\n")
    finally:
        session.close()

    return {
        "retried": len(dead_letters),
        "recoverable": recoverable,
        "unrecoverable": unrecoverable,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the dead-letter backfill process.

    Returns:
        Exit code — 0 on success, 1 on error.
    """
    parser = argparse.ArgumentParser(
        prog="backfill_cli",
        description="Retry unresolved dead-letter records and promote recoverable ones to bronze.",
    )
    parser.add_argument(
        "--db-url",
        default=None,
        metavar="URL",
        help="SQLAlchemy database URL (overrides .env DATABASE_URL).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        metavar="N",
        help="Maximum number of dead-letter records to process (default: 100).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect dead-letter records without modifying the database.",
    )
    args = parser.parse_args(argv)

    try:
        if args.dry_run:
            result = _dry_run(db_url=args.db_url, limit=args.limit)
        else:
            from src.ingestion.backfill import run_dead_letter_backfill

            logger.info("Starting dead-letter backfill  limit=%d", args.limit)
            result = run_dead_letter_backfill(db_url=args.db_url, limit=args.limit)
            print(
                f"\n  Backfill complete → retried={result['retried']}  "
                f"recovered={result['recovered']}  failed={result['failed']}\n"
            )

        return 0
    except Exception as exc:
        logger.exception("Backfill CLI failed.")
        print(f"\n  ERROR: {exc}\n", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
