"""APScheduler-based pipeline scheduler for CareerLens.

Runs the full pipeline (ingestion → transformation → backfill) on a configurable
interval with graceful SIGTERM/SIGINT shutdown.

The default interval is read from the ``PIPELINE_INTERVAL_MINUTES`` environment
variable (default: **5 min**). This is intentionally a near-real-time *batch*
pipeline — job postings change on the order of hours, so 5-minute cycles provide
visible dashboard freshness without the complexity of true streaming.

Usage::

    python -m src.orchestration.scheduler              # default from env (5 min)
    python -m src.orchestration.scheduler --interval 30
    python -m src.orchestration.scheduler --interval 1440  # daily
"""

from __future__ import annotations

import argparse
import signal
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from src.config import settings
from src.ingestion.db import get_session
from src.logger import logger
from src.orchestration.email_alerts import send_job_alerts
from src.orchestration.runner import run_pipeline


def _job(source: str, db_url: str | None, use_dbt: bool) -> None:
    """Scheduled job callback — runs the full CareerLens pipeline."""
    logger.info("Scheduler triggering pipeline run  source=%s  use_dbt=%s", source, use_dbt)
    result = run_pipeline(source=source, db_url=db_url, use_dbt=use_dbt)
    status = result.get("status", "unknown")
    if status == "success":
        ingestion = result.get("ingestion", {})
        transformation = result.get("transformation", {})
        logger.info(
            "Scheduled run complete | valid=%s  silver=%s",
            ingestion.get("valid", "—"),
            transformation.get("silver_jobs", "—"),
        )
        
        # Trigger job alert digests
        logger.info("Scheduler starting email alerts check...")
        session = get_session(db_url=db_url)
        try:
            alerts_sent = send_job_alerts(session, force=False)
            logger.info("Scheduler email alerts check finished. Alerts sent: %d", alerts_sent)
        except Exception as exc:
            logger.error("Error running email alerts dispatch: %s", exc)
        finally:
            session.close()
    else:
        logger.error("Scheduled pipeline run failed: %s", result)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for the recurring pipeline scheduler.

    Returns:
        Exit code — 0 on clean shutdown, 1 on error.
    """
    parser = argparse.ArgumentParser(
        prog="scheduler",
        description="Run the CareerLens pipeline on a recurring schedule.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=settings.pipeline_interval_minutes,
        metavar="MINUTES",
        help=(
            "Interval between pipeline runs in minutes "
            f"(default: {settings.pipeline_interval_minutes} from PIPELINE_INTERVAL_MINUTES)."
        ),
    )
    parser.add_argument(
        "--source",
        default="all",
        choices=["remotive", "kaggle", "all"],
        help="Data source to use (default: all).",
    )
    parser.add_argument(
        "--db-url",
        default=None,
        metavar="URL",
        help="SQLAlchemy database URL override.",
    )
    parser.add_argument(
        "--use-dbt",
        action="store_true",
        help="Use dbt for transformations (requires Postgres).",
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        default=True,
        help="Execute one pipeline run immediately on start (default: True).",
    )
    args = parser.parse_args(argv)

    scheduler = BlockingScheduler(timezone="UTC")
    trigger = IntervalTrigger(minutes=args.interval)

    scheduler.add_job(
        _job,
        trigger=trigger,
        kwargs={
            "source": args.source,
            "db_url": args.db_url,
            "use_dbt": args.use_dbt,
        },
        id="careerlens_pipeline",
        name="CareerLens Pipeline",
        replace_existing=True,
    )

    # Graceful shutdown
    def _shutdown(signum: int, frame: object) -> None:  # noqa: ARG001
        logger.info("Received signal %s — shutting down scheduler.", signum)
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info(
        "CareerLens scheduler started | interval=%d min  source=%s",
        args.interval,
        args.source,
    )

    # Run immediately on start before handing off to the schedule
    if args.run_now:
        logger.info("Running initial pipeline pass before entering schedule loop…")
        _job(source=args.source, db_url=args.db_url, use_dbt=args.use_dbt)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
