"""CareerLens pipeline orchestration entry point.

Runs the full pipeline once (ingestion → transformation → dead-letter backfill)
or delegates to the scheduler for recurring execution.

Usage::

    # Single run, Remotive source (default):
    python -m src.orchestration.runner --source remotive

    # All sources at once (Remotive + RemoteOK + Arbeitnow — thousands of jobs):
    python -m src.orchestration.runner --source all

    # Single run, Kaggle fallback:
    python -m src.orchestration.runner --source kaggle

    # Recurring run every 5 minutes (all sources):
    python -m src.orchestration.runner --source all --schedule-interval 5

    # Single run with dbt transformations (Postgres required):
    python -m src.orchestration.runner --use-dbt
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from src.ingestion.backfill import run_dead_letter_backfill
from src.ingestion.pipeline import run_ingestion
from src.logger import logger
from src.transformation.runner import run_transformations


def run_pipeline(
    source: str = "remotive",
    db_url: str | None = None,
    use_dbt: bool = False,
) -> dict[str, Any]:
    """Run the full CareerLens pipeline in sequence.

    Executes ingestion, transformation, and dead-letter backfill.  If ingestion
    fails the pipeline is aborted and the error is returned without running
    subsequent stages.

    Args:
        source: Primary data source — ``"remotive"`` or ``"kaggle"``.
        db_url: Optional SQLAlchemy-compatible database URL override.
        use_dbt: When *True*, run dbt transformations instead of the Python runner.

    Returns:
        A summary dict with keys: ``status``, ``ingestion``, ``transformation``,
        ``backfill``.
    """
    logger.info("CareerLens orchestration starting  source=%s  use_dbt=%s", source, use_dbt)

    ingestion_result = run_ingestion(source=source, db_url=db_url)
    if ingestion_result.get("status") != "success":
        logger.error("Ingestion failed — aborting pipeline: %s", ingestion_result)
        return {"status": "error", "ingestion": ingestion_result}

    transformation_result = run_transformations(db_url=db_url, use_dbt=use_dbt)
    backfill_result = run_dead_letter_backfill(db_url=db_url)

    result: dict[str, Any] = {
        "status": "success",
        "ingestion": ingestion_result,
        "transformation": transformation_result,
        "backfill": backfill_result,
    }
    logger.info(
        "CareerLens orchestration complete | ingested=%s  silver=%s  backfill_recovered=%s",
        ingestion_result.get("valid"),
        transformation_result.get("silver_jobs", "—"),
        backfill_result.get("recovered"),
    )
    return result


def main() -> None:
    """CLI entry point for the single-run and scheduled pipeline modes."""
    parser = argparse.ArgumentParser(
        prog="runner",
        description="Run the CareerLens data pipeline.",
    )
    parser.add_argument(
        "--source",
        default="all",
        choices=["remotive", "kaggle", "all"],
        help="Primary data source: 'remotive', 'kaggle', or 'all' (Remotive+RemoteOK+Arbeitnow). Default: all.",
    )
    parser.add_argument(
        "--db-url",
        default=None,
        metavar="URL",
        help="SQLAlchemy database URL (overrides DATABASE_URL in .env).",
    )
    parser.add_argument(
        "--use-dbt",
        action="store_true",
        help="Use dbt for transformations (requires Postgres).",
    )
    parser.add_argument(
        "--schedule-interval",
        type=int,
        default=None,
        metavar="MINUTES",
        help="Run on a recurring schedule every N minutes (uses APScheduler).",
    )
    args = parser.parse_args()

    if args.schedule_interval is not None:
        # Delegate to the scheduler module
        from src.orchestration.scheduler import main as scheduler_main

        sys.exit(
            scheduler_main(
                [
                    "--interval",
                    str(args.schedule_interval),
                    "--source",
                    args.source,
                    *(["--use-dbt"] if args.use_dbt else []),
                    *(["--db-url", args.db_url] if args.db_url else []),
                ]
            )
        )
    else:
        result = run_pipeline(
            source=args.source,
            db_url=args.db_url,
            use_dbt=args.use_dbt,
        )
        print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
