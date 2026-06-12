from __future__ import annotations

from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.serving.api.dependencies import get_db
from src.serving.api.schemas import (
    CountryTrendResponse,
    ErrorResponse,
    HealthResponse,
    JobSummaryResponse,
    RoleTrendResponse,
    SkillTrendResponse,
    StatsResponse,
    TimeTrendResponse,
)
from src.serving.api.service import (
    fetch_country_trends,
    fetch_jobs_page,
    fetch_role_trends,
    fetch_skill_trends,
    fetch_stats,
    fetch_time_trends,
)

app = FastAPI(
    title="CareerLens API",
    version="1.0.0",
    description=(
        "REST API for the CareerLens global job market trends pipeline. "
        "Exposes aggregated gold-layer data for country, skill, role, and time dimensions."
    ),
    contact={"name": "CareerLens Team"},
    license_info={"name": "MIT"},
    responses={500: {"model": ErrorResponse}},
)

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def _global_exception_handler(request, exc: Exception) -> JSONResponse:  # type: ignore[type-arg]
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health", response_model=HealthResponse, tags=["system"])
def healthcheck() -> HealthResponse:
    """Return API liveness status."""
    return HealthResponse(status="ok")


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/stats",
    response_model=StatsResponse,
    tags=["stats"],
    summary="Pipeline statistics",
)
def pipeline_stats(session: Session = Depends(get_db)) -> StatsResponse:
    """Return high-level pipeline statistics from live database tables."""
    data = fetch_stats(session)
    return StatsResponse(**data)


# ---------------------------------------------------------------------------
# Trend endpoints
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/trends/countries",
    response_model=list[CountryTrendResponse],
    tags=["trends"],
    summary="Job counts by country",
)
def country_trends(
    limit: int = Query(default=100, ge=1, le=500, description="Max rows to return."),
    month: date | None = Query(
        default=None, description="Filter to a specific month (YYYY-MM-DD)."
    ),
    country: str | None = Query(default=None, description="Substring filter on country name."),
    session: Session = Depends(get_db),
) -> list[CountryTrendResponse]:
    """Return aggregated monthly job counts grouped by country."""
    rows = fetch_country_trends(session, limit, month=month, country=country)
    return [CountryTrendResponse.model_validate(row, from_attributes=True) for row in rows]


@app.get(
    "/api/v1/trends/skills",
    response_model=list[SkillTrendResponse],
    tags=["trends"],
    summary="Job counts by skill",
)
def skill_trends(
    limit: int = Query(default=100, ge=1, le=500, description="Max rows to return."),
    month: date | None = Query(
        default=None, description="Filter to a specific month (YYYY-MM-DD)."
    ),
    skill: str | None = Query(default=None, description="Substring filter on skill name."),
    session: Session = Depends(get_db),
) -> list[SkillTrendResponse]:
    """Return aggregated monthly job counts grouped by skill tag."""
    rows = fetch_skill_trends(session, limit, month=month, skill=skill)
    return [SkillTrendResponse.model_validate(row, from_attributes=True) for row in rows]


@app.get(
    "/api/v1/trends/roles",
    response_model=list[RoleTrendResponse],
    tags=["trends"],
    summary="Job counts by role",
)
def role_trends(
    limit: int = Query(default=100, ge=1, le=500, description="Max rows to return."),
    month: date | None = Query(
        default=None, description="Filter to a specific month (YYYY-MM-DD)."
    ),
    role: str | None = Query(default=None, description="Substring filter on role title."),
    session: Session = Depends(get_db),
) -> list[RoleTrendResponse]:
    """Return aggregated monthly job counts grouped by role title."""
    rows = fetch_role_trends(session, limit, month=month, role=role)
    return [RoleTrendResponse.model_validate(row, from_attributes=True) for row in rows]


@app.get(
    "/api/v1/trends/time",
    response_model=list[TimeTrendResponse],
    tags=["trends"],
    summary="Total job counts over time",
)
def time_trends(
    limit: int = Query(default=100, ge=1, le=500, description="Max rows to return."),
    session: Session = Depends(get_db),
) -> list[TimeTrendResponse]:
    """Return total monthly job counts ordered chronologically."""
    rows = fetch_time_trends(session, limit)
    return [TimeTrendResponse.model_validate(row, from_attributes=True) for row in rows]


# ---------------------------------------------------------------------------
# Job browsing
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/jobs",
    response_model=list[JobSummaryResponse],
    tags=["jobs"],
    summary="Browse bronze job records",
)
def list_jobs(
    page: int = Query(default=1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(default=50, ge=1, le=200, description="Rows per page."),
    source: str | None = Query(default=None, description="Filter by source (remotive/kaggle/remoteok/arbeitnow)."),
    seniority: str | None = Query(default=None, description="Filter by seniority level."),
    min_salary: float | None = Query(default=None, description="Minimum salary threshold."),
    session: Session = Depends(get_db),
) -> list[JobSummaryResponse]:
    """Return a paginated list of bronze-layer job records joined with silver metrics."""
    jobs_data = fetch_jobs_page(
        session, page=page, page_size=page_size, source=source, seniority=seniority, min_salary=min_salary
    )
    if not jobs_data:
        raise HTTPException(status_code=404, detail="No jobs found for the given parameters.")
    return [
        JobSummaryResponse(
            id=bronze.id,
            title=bronze.title,
            company_name=bronze.company_name,
            source=bronze.source,
            country=bronze.candidate_required_location,
            category=bronze.category,
            job_type=bronze.job_type,
            publication_date=bronze.publication_date.isoformat(),
            url=bronze.url,
            salary_min=silver.salary_min if silver else None,
            salary_max=silver.salary_max if silver else None,
            salary_currency=silver.salary_currency if silver else None,
            seniority=silver.seniority if silver else None,
        )
        for bronze, silver in jobs_data
    ]
