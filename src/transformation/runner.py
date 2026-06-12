from __future__ import annotations

import os
import re
import subprocess
from collections import defaultdict
from datetime import date
from typing import Any

from src.config import PROJECT_ROOT, settings
from src.ingestion.db import (
    BronzeJob,
    GoldCountryTrend,
    GoldRoleTrend,
    GoldSkillTrend,
    GoldTimeTrend,
    SilverJob,
    get_session,
    init_db,
    refresh_table,
)
from src.logger import logger


def _first_of_month(value: date) -> date:
    return value.replace(day=1)


def _infer_country(location: str | None) -> str:
    if not location:
        return "Unknown"

    normalized = location.strip()
    lowered = normalized.lower()
    if "worldwide" in lowered or "global" in lowered:
        return "Global"
    if "," in normalized:
        return normalized.split(",")[-1].strip() or "Unknown"
    return normalized or "Unknown"


def _normalize_role(title: str) -> str:
    return " ".join(title.strip().split())


def _parse_salary(salary_str: str | None, description: str | None) -> tuple[float | None, float | None, str | None]:
    text = salary_str or ""
    if not text and description:
        text = description[:1000]
    
    if not text:
        return None, None, None

    currency = "USD"
    if "€" in text or "EUR" in text.upper():
        currency = "EUR"
    elif "£" in text or "GBP" in text.upper():
        currency = "GBP"
    elif "$" in text or "USD" in text.upper():
        currency = "USD"

    is_hourly = False
    if re.search(r'/hr|hour|hourly', text, re.IGNORECASE):
        is_hourly = True

    pattern = r'(?:\$|€|£)?\s*(\d{1,3}(?:,\d{3})*|\d+)\s*([kK])?'
    matches = re.findall(pattern, text)
    
    values = []
    for num_str, k_suffix in matches:
        num = float(num_str.replace(",", ""))
        if k_suffix:
            num *= 1000
        if is_hourly and num < 1000:
            num *= 2000
        
        if 10000 <= num <= 1000000:
            values.append(num)

    if not values:
        single_matches = re.findall(r'(?:\$|€|£)\s*(\d{1,3}(?:,\d{3})*|\d+)\s*([kK])?', text)
        for num_str, k_suffix in single_matches:
            num = float(num_str.replace(",", ""))
            if k_suffix:
                num *= 1000
            if is_hourly and num < 1000:
                num *= 2000
            if 10000 <= num <= 1000000:
                values.append(num)

    if len(values) >= 2:
        sorted_vals = sorted(values)
        return sorted_vals[0], sorted_vals[-1], currency
    elif len(values) == 1:
        return values[0], values[0], currency

    return None, None, None


def _classify_seniority(title: str, description: str | None) -> str:
    text = (title + " " + (description or "")).lower()
    if any(kw in text for kw in ["lead", "principal", "director", "head", "vp", "chief", "executive", "architect"]):
        return "Lead"
    if any(kw in text for kw in ["senior", "sr.", "sr ", "mid-senior", "experienced", "expert"]):
        return "Senior"
    if any(kw in text for kw in ["junior", "jr.", "jr ", "entry", "intern", "associate", "graduate", "trainee"]):
        return "Junior"
    return "Mid-level"


def _build_silver_rows(bronze_jobs: list[BronzeJob]) -> list[dict[str, Any]]:
    rows = []
    for job in bronze_jobs:
        published_date = job.publication_date.date()
        sal_min, sal_max, currency = _parse_salary(job.salary, job.description)
        seniority = _classify_seniority(job.title, job.description)
        rows.append(
            {
                "job_id": job.id,
                "source": job.source,
                "title": job.title,
                "company_name": job.company_name,
                "category": job.category,
                "role": _normalize_role(job.title),
                "country": _infer_country(job.candidate_required_location),
                "tags": job.tags or [],
                "publication_date": job.publication_date,
                "published_date": published_date,
                "published_month": _first_of_month(published_date),
                "salary_min": sal_min,
                "salary_max": sal_max,
                "salary_currency": currency,
                "seniority": seniority,
            }
        )
    return rows




def _aggregate_country_trends(silver_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: defaultdict[tuple[str, date], int] = defaultdict(int)
    for row in silver_rows:
        counts[(row["country"], row["published_month"])] += 1
    return [
        {"country": country, "published_month": month, "job_count": count}
        for (country, month), count in sorted(
            counts.items(),
            key=lambda item: (item[0][1], item[0][0]),
        )
    ]


def _aggregate_skill_trends(silver_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: defaultdict[tuple[str, date], int] = defaultdict(int)
    for row in silver_rows:
        for tag in row["tags"]:
            counts[(tag, row["published_month"])] += 1
    return [
        {"skill": skill, "published_month": month, "job_count": count}
        for (skill, month), count in sorted(
            counts.items(),
            key=lambda item: (item[0][1], item[0][0]),
        )
    ]


def _aggregate_role_trends(silver_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: defaultdict[tuple[str, date], int] = defaultdict(int)
    for row in silver_rows:
        counts[(row["role"], row["published_month"])] += 1
    return [
        {"role": role, "published_month": month, "job_count": count}
        for (role, month), count in sorted(
            counts.items(),
            key=lambda item: (item[0][1], item[0][0]),
        )
    ]


def _aggregate_time_trends(silver_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: defaultdict[date, int] = defaultdict(int)
    for row in silver_rows:
        counts[row["published_month"]] += 1
    return [
        {"published_month": month, "job_count": count}
        for month, count in sorted(counts.items(), key=lambda item: item[0])
    ]


def run_transformations_python(db_url: str | None = None) -> dict[str, int]:
    """Build silver and gold tables using Python for local tests and SQLite."""

    init_db(db_url=db_url)
    session = get_session(db_url=db_url)
    try:
        bronze_jobs = session.query(BronzeJob).all()
        silver_rows = _build_silver_rows(bronze_jobs)

        refresh_table(session, SilverJob, silver_rows)
        refresh_table(session, GoldCountryTrend, _aggregate_country_trends(silver_rows))
        refresh_table(session, GoldSkillTrend, _aggregate_skill_trends(silver_rows))
        refresh_table(session, GoldRoleTrend, _aggregate_role_trends(silver_rows))
        refresh_table(session, GoldTimeTrend, _aggregate_time_trends(silver_rows))
    finally:
        session.close()

    result = {
        "bronze_jobs": len(bronze_jobs),
        "silver_jobs": len(silver_rows),
        "gold_country_trends": len(_aggregate_country_trends(silver_rows)),
        "gold_skill_trends": len(_aggregate_skill_trends(silver_rows)),
        "gold_role_trends": len(_aggregate_role_trends(silver_rows)),
        "gold_time_trends": len(_aggregate_time_trends(silver_rows)),
    }
    logger.info("Python transformations completed: %s", result)
    return result


def run_transformations_dbt(db_url: str | None = None) -> dict[str, str]:
    """Run dbt models and tests for the Postgres-backed transformation layer."""

    project_dir = PROJECT_ROOT / "src" / "transformation"
    profiles_dir = project_dir

    env = os.environ.copy()
    env.setdefault("POSTGRES_USER", settings.postgres_user)
    env.setdefault("POSTGRES_PASSWORD", settings.postgres_password)
    env.setdefault("POSTGRES_HOST", settings.postgres_host)
    env.setdefault("POSTGRES_PORT", str(settings.postgres_port))
    env.setdefault("POSTGRES_DB", settings.postgres_db)
    if db_url:
        env["DATABASE_URL"] = db_url

    commands = [
        ["dbt", "run", "--project-dir", str(project_dir), "--profiles-dir", str(profiles_dir)],
        ["dbt", "test", "--project-dir", str(project_dir), "--profiles-dir", str(profiles_dir)],
    ]
    for command in commands:
        logger.info("Running transformation command: %s", " ".join(command))
        subprocess.run(command, cwd=project_dir, env=env, check=True)

    return {"status": "success", "runner": "dbt"}


def run_transformations(db_url: str | None = None, use_dbt: bool = False) -> dict[str, Any]:
    """Run transformations using dbt or the local Python fallback."""

    if use_dbt:
        return run_transformations_dbt(db_url=db_url)
    return run_transformations_python(db_url=db_url)
