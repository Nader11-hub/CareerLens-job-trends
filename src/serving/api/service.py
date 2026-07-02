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
    SilverJob,
    EmailSubscription,
    BookmarkedJob,
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
    seniority: str | None = None,
    min_salary: float | None = None,
) -> list[tuple[BronzeJob, SilverJob]]:
    """Return a paginated page of bronze jobs joined with silver jobs for enrichment and filtering.

    Args:
        session: Active SQLAlchemy session.
        page: 1-based page number.
        page_size: Rows per page (max 200).
        source: Optional source filter.
        seniority: Optional seniority level filter.
        min_salary: Optional minimum salary threshold.

    Returns:
        List of (BronzeJob, SilverJob) tuples for the requested page.
    """
    page_size = min(page_size, 200)
    offset = (max(page, 1) - 1) * page_size
    q = session.query(BronzeJob, SilverJob).outerjoin(SilverJob, BronzeJob.id == SilverJob.job_id)
    if source:
        q = q.filter(BronzeJob.source == source)
    if seniority:
        q = q.filter(SilverJob.seniority.ilike(seniority))
    if min_salary is not None:
        q = q.filter(SilverJob.salary_max >= min_salary)
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


def create_or_update_subscription(
    session: Session,
    name: str,
    email: str,
    skills: list[str],
) -> EmailSubscription:
    """Create a new job alert subscription or reactivate/update an existing one.

    Args:
        session: Active SQLAlchemy session.
        name: Name of the subscriber.
        email: Email address of the subscriber.
        skills: List of skills to filter jobs by.

    Returns:
        The created or updated EmailSubscription ORM model.
    """
    # Normalize email to lowercase
    normalized_email = email.strip().lower()
    
    # Check if subscription already exists
    sub = (
        session.query(EmailSubscription)
        .filter(EmailSubscription.email == normalized_email)
        .first()
    )
    
    # Skills normalization
    normalized_skills = [s.strip().lower() for s in skills if s.strip()]
    
    if sub:
        # Update existing subscription and reactivate it
        sub.name = name.strip()
        sub.skills = normalized_skills
        sub.active = True
        session.commit()
        session.refresh(sub)
        return sub
    else:
        # Create a new subscription
        new_sub = EmailSubscription(
            name=name.strip(),
            email=normalized_email,
            skills=normalized_skills,
            active=True,
        )
        session.add(new_sub)
        session.commit()
        session.refresh(new_sub)
        return new_sub


def unsubscribe_email(session: Session, email: str) -> bool:
    """Deactivate subscription for the given email address.

    Args:
        session: Active SQLAlchemy session.
        email: Email address to unsubscribe.

    Returns:
        True if the subscription was found and deactivated, False otherwise.
    """
    normalized_email = email.strip().lower()
    sub = (
        session.query(EmailSubscription)
        .filter(EmailSubscription.email == normalized_email)
        .first()
    )
    if sub and sub.active:
        sub.active = False
        session.commit()
        return True
    return False


# ---------------------------------------------------------------------------
# Bookmark helpers
# ---------------------------------------------------------------------------


def get_bookmarks(session: Session) -> list[BookmarkedJob]:
    """Return all bookmarked jobs ordered by most recently saved."""
    return (
        session.query(BookmarkedJob)
        .order_by(BookmarkedJob.bookmarked_at.desc())
        .all()
    )


def add_bookmark(session: Session, job_id: int, notes: str | None = None) -> BookmarkedJob:
    """Bookmark a job by its bronze-layer ID.

    If the job is already bookmarked the existing record is returned unchanged.

    Args:
        session: Active SQLAlchemy session.
        job_id: ID of the BronzeJob to bookmark.
        notes: Optional personal note to attach.

    Returns:
        The created or existing :class:`BookmarkedJob` record.
    """
    existing = session.query(BookmarkedJob).filter(BookmarkedJob.job_id == job_id).first()
    if existing:
        return existing
    bookmark = BookmarkedJob(job_id=job_id, notes=notes)
    session.add(bookmark)
    session.commit()
    session.refresh(bookmark)
    return bookmark


def remove_bookmark(session: Session, job_id: int) -> bool:
    """Delete a bookmark by bronze job ID.

    Args:
        session: Active SQLAlchemy session.
        job_id: ID of the BronzeJob whose bookmark to remove.

    Returns:
        True if a bookmark was found and deleted, False otherwise.
    """
    bookmark = session.query(BookmarkedJob).filter(BookmarkedJob.job_id == job_id).first()
    if bookmark:
        session.delete(bookmark)
        session.commit()
        return True
    return False


def update_bookmark_notes(session: Session, job_id: int, notes: str | None) -> BookmarkedJob | None:
    """Update the personal notes on an existing bookmark.

    Args:
        session: Active SQLAlchemy session.
        job_id: ID of the BronzeJob whose bookmark to update.
        notes: New notes string (or None to clear).

    Returns:
        The updated :class:`BookmarkedJob`, or None if not found.
    """
    bookmark = session.query(BookmarkedJob).filter(BookmarkedJob.job_id == job_id).first()
    if not bookmark:
        return None
    bookmark.notes = notes
    session.commit()
    session.refresh(bookmark)
    return bookmark


# ---------------------------------------------------------------------------
# Salary Intelligence
# ---------------------------------------------------------------------------

def fetch_salary_by_role(
    session: Session,
    currency: str = "USD",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Aggregate average/min/max salary per job role from silver_jobs.

    Only includes rows that have both salary_min and salary_max populated.
    """
    rows = (
        session.query(
            SilverJob.role,
            func.avg((SilverJob.salary_min + SilverJob.salary_max) / 2).label("avg_salary"),
            func.min(SilverJob.salary_min).label("min_salary"),
            func.max(SilverJob.salary_max).label("max_salary"),
            func.count(SilverJob.job_id).label("job_count"),
        )
        .filter(
            SilverJob.salary_min.isnot(None),
            SilverJob.salary_max.isnot(None),
            SilverJob.salary_currency == currency,
        )
        .group_by(SilverJob.role)
        .order_by(func.avg((SilverJob.salary_min + SilverJob.salary_max) / 2).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "role": r.role,
            "avg_salary": round(float(r.avg_salary), 2),
            "min_salary": round(float(r.min_salary), 2),
            "max_salary": round(float(r.max_salary), 2),
            "job_count": r.job_count,
            "currency": currency,
        }
        for r in rows
    ]


def fetch_salary_by_country(
    session: Session,
    currency: str = "USD",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Aggregate average/min/max salary per country from silver_jobs."""
    rows = (
        session.query(
            SilverJob.country,
            func.avg((SilverJob.salary_min + SilverJob.salary_max) / 2).label("avg_salary"),
            func.min(SilverJob.salary_min).label("min_salary"),
            func.max(SilverJob.salary_max).label("max_salary"),
            func.count(SilverJob.job_id).label("job_count"),
        )
        .filter(
            SilverJob.salary_min.isnot(None),
            SilverJob.salary_max.isnot(None),
            SilverJob.salary_currency == currency,
            SilverJob.country.notin_(["Unknown", "Global", "Worldwide", "Remote"]),
        )
        .group_by(SilverJob.country)
        .order_by(func.avg((SilverJob.salary_min + SilverJob.salary_max) / 2).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "country": r.country,
            "avg_salary": round(float(r.avg_salary), 2),
            "min_salary": round(float(r.min_salary), 2),
            "max_salary": round(float(r.max_salary), 2),
            "job_count": r.job_count,
            "currency": currency,
        }
        for r in rows
    ]


def fetch_available_salary_currencies(session: Session) -> list[str]:
    """Return distinct salary currencies available in silver_jobs."""
    rows = (
        session.query(SilverJob.salary_currency)
        .filter(SilverJob.salary_currency.isnot(None), SilverJob.salary_min.isnot(None))
        .distinct()
        .all()
    )
    return sorted([r[0] for r in rows if r[0]])


# ---------------------------------------------------------------------------
# Email alert trigger
# ---------------------------------------------------------------------------

def trigger_email_alerts(session: Session, force: bool = True) -> int:
    """Trigger email alerts for all active subscribers.

    Returns:
        Number of alerts sent.
    """
    from src.orchestration.email_alerts import send_job_alerts
    return send_job_alerts(session, force=force)


# ---------------------------------------------------------------------------
# AI-powered Job Recommendations
# ---------------------------------------------------------------------------

def ai_recommend_jobs(
    session: Session,
    resume_text: str,
    top_n: int = 10,
) -> dict[str, Any]:
    """Use Gemini AI to analyse resume text and recommend matching jobs.

    Falls back to keyword matching if no API key is configured.
    """
    import re
    from src.config import settings

    extracted_skills: list[str] = []
    recommended_roles: list[str] = []
    ai_summary: str = ""

    # ── Try Gemini ────────────────────────────────────────────────────────
    if settings.gemini_api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.gemini_api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")

            prompt = f"""You are a career advisor AI. Analyse the following resume/skills text and respond with ONLY a JSON object (no markdown, no code blocks) in this exact format:
{{
  "summary": "2-3 sentence career profile summary",
  "skills": ["skill1", "skill2", ...],
  "recommended_roles": ["role1", "role2", "role3", "role4", "role5"]
}}

Resume/Skills text:
{resume_text[:3000]}"""

            response = model.generate_content(prompt)
            raw = response.text.strip()
            # Strip markdown code fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            import json
            data = json.loads(raw)
            extracted_skills = [s.lower().strip() for s in data.get("skills", [])]
            recommended_roles = data.get("recommended_roles", [])
            ai_summary = data.get("summary", "")
        except Exception as exc:
            ai_summary = f"AI analysis unavailable ({exc}). Showing keyword-based matches."

    # ── Keyword-based fallback / skill extraction ─────────────────────────
    if not extracted_skills:
        stopwords = {
            "and", "the", "with", "for", "from", "using", "experience",
            "work", "skills", "development", "software", "role", "job",
            "years", "team", "strong", "knowledge", "ability",
        }
        tokens = re.findall(r'\b[a-zA-Z0-9+#\-\.]+\b', resume_text.lower())
        extracted_skills = list({
            t for t in tokens
            if t not in stopwords and (len(t) > 1 or t in ("c", "r", "go"))
        })[:30]

    if not ai_summary:
        ai_summary = (
            f"Keyword analysis identified {len(extracted_skills)} skills. "
            "Configure GEMINI_API_KEY in .env for AI-powered career insights."
        )

    # ── Match jobs from database ──────────────────────────────────────────
    skill_set = set(extracted_skills)
    role_set = {r.lower() for r in recommended_roles}

    candidates = (
        session.query(BronzeJob, SilverJob)
        .outerjoin(SilverJob, BronzeJob.id == SilverJob.job_id)
        .order_by(BronzeJob.publication_date.desc())
        .limit(2000)
        .all()
    )

    scored: list[tuple[int, BronzeJob, SilverJob | None]] = []
    for bronze, silver in candidates:
        job_tags = {t.lower() for t in (bronze.tags or [])}
        title_words = set(re.findall(r'\b[a-zA-Z0-9+#\-\.]+\b', bronze.title.lower()))
        job_terms = job_tags | title_words

        skill_matches = len(skill_set & job_terms)
        role_bonus = 2 if any(r in bronze.title.lower() for r in role_set) else 0
        score = skill_matches + role_bonus

        if score > 0:
            if len(skill_set) > 0:
                match_percent = int((skill_matches / len(skill_set)) * 100)
                if role_bonus > 0:
                    match_percent = min(100, match_percent + 15)
            else:
                match_percent = 100 if role_bonus > 0 else 0
            scored.append((score, match_percent, bronze, silver))

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)

    matched_jobs = []
    for _, match_percent, bronze, silver in scored[:top_n]:
        matched_jobs.append({
            "id": bronze.id,
            "title": bronze.title,
            "company_name": bronze.company_name,
            "source": bronze.source,
            "country": bronze.candidate_required_location,
            "category": bronze.category,
            "job_type": bronze.job_type,
            "publication_date": bronze.publication_date.isoformat(),
            "url": bronze.url,
            "salary_min": silver.salary_min if silver else None,
            "salary_max": silver.salary_max if silver else None,
            "salary_currency": silver.salary_currency if silver else None,
            "seniority": silver.seniority if silver else None,
            "match_score": match_percent,
            "tags": bronze.tags,
        })

    return {
        "ai_summary": ai_summary,
        "extracted_skills": extracted_skills[:20],
        "recommended_roles": recommended_roles,
        "matched_jobs": matched_jobs,
    }
