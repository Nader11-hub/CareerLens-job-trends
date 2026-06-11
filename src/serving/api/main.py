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
    session: Session = Depends(get_db),
) -> list[JobSummaryResponse]:
    """Return a paginated list of bronze-layer job records."""
    jobs = fetch_jobs_page(session, page=page, page_size=page_size, source=source)
    if not jobs:
        raise HTTPException(status_code=404, detail="No jobs found for the given parameters.")
    return [
        JobSummaryResponse(
            id=j.id,
            title=j.title,
            company_name=j.company_name,
            source=j.source,
            country=j.candidate_required_location,
            category=j.category,
            job_type=j.job_type,
            publication_date=j.publication_date.isoformat(),
            url=j.url,
        )
        for j in jobs
    ]


# ---------------------------------------------------------------------------
# Database catalog
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/database/tables",
    tags=["database"],
    summary="List all tables, row counts, and schemas",
)
def list_database_tables(session: Session = Depends(get_db)) -> dict:
    """Return all table names, their row counts, and column schemas."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(session.bind)
        table_names = inspector.get_table_names()
        result = {}
        for name in table_names:
            # Query row count
            count_res = session.execute(text(f"SELECT count(*) FROM {name}"))
            row_count = count_res.scalar()
            
            # Extract column schemas
            columns = []
            for col in inspector.get_columns(name):
                columns.append({
                    "name": col["name"],
                    "type": str(col["type"])
                })
            result[name] = {
                "row_count": row_count,
                "columns": columns
            }
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database inspection failed: {str(exc)}")


@app.get(
    "/api/v1/database/table/{table_name}",
    tags=["database"],
    summary="Get paginated raw table data",
)
def get_table_data(
    table_name: str,
    page: int = Query(default=1, ge=1, description="Page number (1-based)."),
    page_size: int = Query(default=50, ge=1, le=100, description="Rows per page."),
    session: Session = Depends(get_db),
) -> dict:
    """Return paginated raw records from a specific database table."""
    try:
        from sqlalchemy import inspect, text
        inspector = inspect(session.bind)
        table_names = inspector.get_table_names()
        if table_name not in table_names:
            raise HTTPException(status_code=404, detail=f"Table '{table_name}' does not exist.")
            
        offset = (page - 1) * page_size
        
        # Query total count
        count_res = session.execute(text(f"SELECT count(*) FROM {table_name}"))
        total_rows = count_res.scalar()
        
        # Get column names
        columns = [col["name"] for col in inspector.get_columns(table_name)]
        
        # Query rows safely (table_name is validated against inspector list)
        rows_res = session.execute(text(f"SELECT * FROM {table_name} LIMIT {page_size} OFFSET {offset}"))
        
        rows = []
        for r in rows_res.fetchall():
            row_dict = {}
            for col, val in zip(columns, r):
                if hasattr(val, "isoformat"):
                    row_dict[col] = val.isoformat()
                elif hasattr(val, "strftime"):
                    row_dict[col] = val.strftime("%Y-%m-%d")
                else:
                    row_dict[col] = val
            rows.append(row_dict)
            
        return {
            "table_name": table_name,
            "total_rows": total_rows,
            "page": page,
            "page_size": page_size,
            "columns": columns,
            "rows": rows
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to query table: {str(exc)}")

