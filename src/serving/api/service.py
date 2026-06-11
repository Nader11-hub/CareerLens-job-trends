from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.ingestion.db import (
    BronzeJob,
    BronzeJobDeadLetter,
    GoldCountryTrend,
    GoldRoleTrend,
    GoldSkillTrend,
    GoldTimeTrend,
)


def fetch_country_trends(
    session: Session,
    limit: int = 100,
    month: date | None = None,
    country: str | None = None,
) -> list[GoldCountryTrend]:
    """Query gold country-trend rows with optional filters.

    Args:
        session: Active SQLAlchemy session.
        limit: Maximum rows to return.
        month: Filter to a specific month (first day of month).
        country: Case-insensitive prefix filter on country name.

    Returns:
        Ordered list of :class:`GoldCountryTrend` ORM instances.
    """
    q = session.query(GoldCountryTrend)
    if month:
        q = q.filter(GoldCountryTrend.published_month == month)
    if country:
        q = q.filter(GoldCountryTrend.country.ilike(f"%{country}%"))
    return (
        q.order_by(GoldCountryTrend.published_month.desc(), GoldCountryTrend.job_count.desc())
        .limit(limit)
        .all()
    )


def fetch_skill_trends(
    session: Session,
    limit: int = 100,
    month: date | None = None,
    skill: str | None = None,
) -> list[GoldSkillTrend]:
    """Query gold skill-trend rows with optional filters.

    Args:
        session: Active SQLAlchemy session.
        limit: Maximum rows to return.
        month: Filter to a specific month.
        skill: Case-insensitive substring filter on skill name.

    Returns:
        Ordered list of :class:`GoldSkillTrend` ORM instances.
    """
    q = session.query(GoldSkillTrend)
    if month:
        q = q.filter(GoldSkillTrend.published_month == month)
    if skill:
        q = q.filter(GoldSkillTrend.skill.ilike(f"%{skill}%"))
    return (
        q.order_by(GoldSkillTrend.published_month.desc(), GoldSkillTrend.job_count.desc())
        .limit(limit)
        .all()
    )


def fetch_role_trends(
    session: Session,
    limit: int = 100,
    month: date | None = None,
    role: str | None = None,
) -> list[GoldRoleTrend]:
    """Query gold role-trend rows with optional filters.

    Args:
        session: Active SQLAlchemy session.
        limit: Maximum rows to return.
        month: Filter to a specific month.
        role: Case-insensitive substring filter on role name.

    Returns:
        Ordered list of :class:`GoldRoleTrend` ORM instances.
    """
    q = session.query(GoldRoleTrend)
    if month:
        q = q.filter(GoldRoleTrend.published_month == month)
    if role:
        q = q.filter(GoldRoleTrend.role.ilike(f"%{role}%"))
    return (
        q.order_by(GoldRoleTrend.published_month.desc(), GoldRoleTrend.job_count.desc())
        .limit(limit)
        .all()
    )


def fetch_time_trends(
    session: Session,
    limit: int = 100,
) -> list[GoldTimeTrend]:
    """Query gold time-trend rows ordered chronologically.

    Args:
        session: Active SQLAlchemy session.
        limit: Maximum rows to return.

    Returns:
        Chronologically ordered list of :class:`GoldTimeTrend` ORM instances.
    """
    return (
        session.query(GoldTimeTrend)
        .order_by(GoldTimeTrend.published_month.asc())
        .limit(limit)
        .all()
    )


def fetch_jobs_page(
    session: Session,
    page: int = 1,
    page_size: int = 50,
    source: str | None = None,
) -> list[BronzeJob]:
    """Return a paginated page of bronze jobs.

    Args:
        session: Active SQLAlchemy session.
        page: 1-based page number.
        page_size: Rows per page (max 200).
        source: Optional source filter.

    Returns:
        List of :class:`BronzeJob` ORM instances for the requested page.
    """
    page_size = min(page_size, 200)
    offset = (max(page, 1) - 1) * page_size
    q = session.query(BronzeJob)
    if source:
        q = q.filter(BronzeJob.source == source)
    return q.order_by(BronzeJob.publication_date.desc()).offset(offset).limit(page_size).all()


def fetch_stats(session: Session) -> dict[str, Any]:
    """Aggregate pipeline-level statistics from live database tables.

    Args:
        session: Active SQLAlchemy session.

    Returns:
        Dictionary suitable for building a :class:`StatsResponse`.
    """
    total_jobs = session.query(func.count(BronzeJob.id)).scalar() or 0
    total_dead_letters = (
        session.query(func.count(BronzeJobDeadLetter.id))
        .filter(BronzeJobDeadLetter.resolved.is_(False))
        .scalar()
        or 0
    )

    sources_rows = session.query(BronzeJob.source).distinct().all()
    sources = [r[0] for r in sources_rows]

    date_range = session.query(
        func.min(BronzeJob.publication_date),
        func.max(BronzeJob.publication_date),
    ).one()
    earliest = date_range[0].date() if date_range[0] else None
    latest = date_range[1].date() if date_range[1] else None

    total_countries = (
        session.query(func.count(func.distinct(GoldCountryTrend.country))).scalar() or 0
    )
    total_skills = session.query(func.count(func.distinct(GoldSkillTrend.skill))).scalar() or 0

    return {
        "total_jobs": total_jobs,
        "total_dead_letters": total_dead_letters,
        "sources": sources,
        "earliest_job": earliest,
        "latest_job": latest,
        "total_countries": total_countries,
        "total_skills": total_skills,
    }
