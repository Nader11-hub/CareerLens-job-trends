from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Integer, String, Text, Float, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from src.config import settings
from src.logger import logger


class Base(DeclarativeBase):
    """Shared SQLAlchemy declarative base."""


class BronzeJob(Base):
    """Raw validated jobs stored in the bronze layer."""

    __tablename__ = "bronze_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="remotive")
    url: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    company_logo: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    job_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    publication_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    candidate_required_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    salary: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class BronzeJobDeadLetter(Base):
    """Invalid records captured during ingestion for later backfill."""

    __tablename__ = "bronze_jobs_dead_letter"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="remotive")
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SilverJob(Base):
    """Normalized analytics-ready job records."""

    __tablename__ = "silver_jobs"

    job_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    company_name: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    country: Mapped[str] = mapped_column(String(120), nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    publication_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    published_date: Mapped[date] = mapped_column(Date, nullable=False)
    published_month: Mapped[date] = mapped_column(Date, nullable=False)
    salary_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(String(10), nullable=True)
    seniority: Mapped[str | None] = mapped_column(String(50), nullable=True)


class GoldCountryTrend(Base):
    """Aggregated job counts by country and month."""

    __tablename__ = "gold_country_trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country: Mapped[str] = mapped_column(String(120), nullable=False)
    published_month: Mapped[date] = mapped_column(Date, nullable=False)
    job_count: Mapped[int] = mapped_column(Integer, nullable=False)


class GoldSkillTrend(Base):
    """Aggregated job counts by skill and month."""

    __tablename__ = "gold_skill_trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill: Mapped[str] = mapped_column(String(120), nullable=False)
    published_month: Mapped[date] = mapped_column(Date, nullable=False)
    job_count: Mapped[int] = mapped_column(Integer, nullable=False)


class GoldRoleTrend(Base):
    """Aggregated job counts by role and month."""

    __tablename__ = "gold_role_trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(200), nullable=False)
    published_month: Mapped[date] = mapped_column(Date, nullable=False)
    job_count: Mapped[int] = mapped_column(Integer, nullable=False)


class GoldTimeTrend(Base):
    """Aggregated overall job counts by month."""

    __tablename__ = "gold_time_trends"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    published_month: Mapped[date] = mapped_column(Date, nullable=False)
    job_count: Mapped[int] = mapped_column(Integer, nullable=False)


_engines: dict[str, Engine] = {}
_sessionmakers: dict[str, sessionmaker[Session]] = {}


def _build_engine(url: str) -> Engine:
    if url in {"sqlite://", "sqlite:///:memory:"}:
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            future=True,
        )
    if url.startswith("sqlite:///"):
        return create_engine(url, connect_args={"check_same_thread": False}, future=True)
    return create_engine(url, future=True)


def get_engine(db_url: str | None = None) -> Engine:
    """Return a cached database engine."""

    url = db_url or settings.database_url
    if url not in _engines:
        _engines[url] = _build_engine(url)
    return _engines[url]


def get_session(*args: Any, db_url: str | None = None, engine: Engine | None = None) -> Session:
    """Create a session from either an engine or a database URL."""

    bind = engine
    if args and bind is None and db_url is None:
        first = args[0]
        if isinstance(first, Engine):
            bind = first
        elif isinstance(first, str):
            db_url = first

    bind = bind or get_engine(db_url)
    key = str(bind.url)
    if key not in _sessionmakers:
        _sessionmakers[key] = sessionmaker(
            bind=bind,
            autoflush=False,
            autocommit=False,
            future=True,
        )
    return _sessionmakers[key]()


def init_db(db_url: str | None = None, engine: Engine | None = None) -> None:
    """Create all required tables."""

    bind = engine or get_engine(db_url)
    logger.info("Initializing database schemas...")
    Base.metadata.create_all(bind=bind)
    logger.info("Database schemas initialized.")


def upsert_bronze_jobs(session: Session, jobs: Iterable[dict[str, Any]]) -> int:
    """Upsert validated bronze jobs across SQLite and PostgreSQL."""

    count = 0
    for job in jobs:
        session.merge(BronzeJob(**job))
        count += 1
    session.commit()
    return count


def insert_dead_letters(session: Session, errors: Iterable[dict[str, Any]]) -> int:
    """Insert invalid raw records into the dead-letter table."""

    dead_letters = [
        BronzeJobDeadLetter(
            source=error.get("source", "unknown"),
            raw_data=error["raw_data"],
            error_message=error["error_message"],
        )
        for error in errors
    ]
    if not dead_letters:
        return 0
    session.add_all(dead_letters)
    session.commit()
    return len(dead_letters)


def fetch_unresolved_dead_letters(session: Session, limit: int = 100) -> list[BronzeJobDeadLetter]:
    """Return unresolved dead-letter records ordered by oldest first."""

    return (
        session.query(BronzeJobDeadLetter)
        .filter(BronzeJobDeadLetter.resolved.is_(False))
        .order_by(BronzeJobDeadLetter.created_at.asc())
        .limit(limit)
        .all()
    )


def mark_dead_letters_resolved(session: Session, dead_letter_ids: Iterable[int]) -> int:
    """Mark the provided dead-letter rows as resolved."""

    ids = list(dead_letter_ids)
    if not ids:
        return 0
    rows = session.query(BronzeJobDeadLetter).filter(BronzeJobDeadLetter.id.in_(ids)).all()
    for row in rows:
        row.resolved = True
        row.resolved_at = datetime.now(UTC)
    session.commit()
    return len(rows)


def increment_dead_letter_retries(session: Session, dead_letter_ids: Iterable[int]) -> int:
    """Increment retry counts for dead letters that still fail during backfill."""

    ids = list(dead_letter_ids)
    if not ids:
        return 0
    rows = session.query(BronzeJobDeadLetter).filter(BronzeJobDeadLetter.id.in_(ids)).all()
    for row in rows:
        row.retry_count += 1
    session.commit()
    return len(rows)


def refresh_table(session: Session, model: type[Base], rows: Iterable[dict[str, Any]]) -> int:
    """Replace all rows for a model with the provided records."""

    session.query(model).delete()
    payload = [model(**row) for row in rows]
    if payload:
        session.add_all(payload)
    session.commit()
    return len(payload)
