from __future__ import annotations

from datetime import date

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from src.serving.api.auth import get_current_user, require_admin
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
    SubscriptionCreate,
    SubscriptionResponse,
    UnsubscribeRequest,
    BookmarkCreate,
    BookmarkResponse,
    BookmarkNoteUpdate,
    SalaryByRoleResponse,
    SalaryByCountryResponse,
    AIRecommendRequest,
    AIRecommendResponse,
    AlertTriggerResponse,
    # Auth schemas
    UserRegister,
    UserLogin,
    TokenResponse,
    UserResponse,
    RoleUpdate,
)
from src.serving.api.service import (
    fetch_country_trends,
    fetch_jobs_page,
    fetch_role_trends,
    fetch_skill_trends,
    fetch_stats,
    fetch_time_trends,
    create_or_update_subscription,
    unsubscribe_email,
    get_bookmarks,
    add_bookmark,
    remove_bookmark,
    update_bookmark_notes,
    fetch_salary_by_role,
    fetch_salary_by_country,
    fetch_available_salary_currencies,
    trigger_email_alerts,
    ai_recommend_jobs,
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
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def _global_exception_handler(request, exc: Exception) -> JSONResponse:  # type: ignore[type-arg]
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ---------------------------------------------------------------------------
# Health and Redirects
# ---------------------------------------------------------------------------


@app.get("/", include_in_schema=False)
def root_redirect() -> RedirectResponse:
    """Redirect root path to interactive OpenAPI documentation."""
    return RedirectResponse(url="/docs")


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
            tags=bronze.tags,
        )
        for bronze, silver in jobs_data
    ]


# ---------------------------------------------------------------------------
# Job alert email subscriptions
# ---------------------------------------------------------------------------


@app.post(
    "/api/v1/subscriptions",
    response_model=SubscriptionResponse,
    status_code=201,
    tags=["subscriptions"],
    summary="Create or update an email subscription",
)
def subscribe(
    payload: SubscriptionCreate,
    session: Session = Depends(get_db),
) -> SubscriptionResponse:
    """Create a new job-alert subscription or reactivate/update an existing one."""
    sub = create_or_update_subscription(
        session, name=payload.name, email=payload.email, skills=payload.skills
    )
    return SubscriptionResponse(
        id=sub.id,
        name=sub.name,
        email=sub.email,
        skills=sub.skills,
        active=sub.active,
        created_at=sub.created_at.isoformat(),
        last_sent_at=sub.last_sent_at.isoformat() if sub.last_sent_at else None,
    )


@app.post(
    "/api/v1/subscriptions/unsubscribe",
    tags=["subscriptions"],
    summary="Unsubscribe an email address",
)
def unsubscribe(
    payload: UnsubscribeRequest,
    session: Session = Depends(get_db),
) -> dict[str, str]:
    """Deactivate subscription for the given email address."""
    success = unsubscribe_email(session, email=payload.email)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"No active subscription found for email: {payload.email}",
        )
    return {"message": f"Successfully unsubscribed {payload.email} from job alerts."}


# ---------------------------------------------------------------------------
# Bookmarked Jobs Endpoints
# ---------------------------------------------------------------------------


@app.get(
    "/api/v1/bookmarks",
    response_model=list[BookmarkResponse],
    summary="Get all bookmarked jobs",
)
def list_bookmarks(session: Session = Depends(get_db)) -> list[BookmarkResponse]:
    """Retrieve the list of bookmarked jobs, sorted by bookmark date descending."""
    from src.ingestion.db import BookmarkedJob, BronzeJob
    results = (
        session.query(BookmarkedJob, BronzeJob)
        .outerjoin(BronzeJob, BookmarkedJob.job_id == BronzeJob.id)
        .order_by(BookmarkedJob.bookmarked_at.desc())
        .all()
    )
    return [
        BookmarkResponse(
            id=b.id,
            job_id=b.job_id,
            notes=b.notes,
            bookmarked_at=b.bookmarked_at.isoformat(),
            title=job.title if job else "Unknown (Deleted)",
            company_name=job.company_name if job else "Unknown Company",
            url=job.url if job else None,
            source=job.source if job else "unknown",
        )
        for b, job in results
    ]


@app.post(
    "/api/v1/bookmarks",
    response_model=BookmarkResponse,
    status_code=201,
    summary="Bookmark a job posting",
)
def create_bookmark(
    payload: BookmarkCreate,
    session: Session = Depends(get_db),
) -> BookmarkResponse:
    """Bookmark a job posting by its ID with optional notes."""
    b = add_bookmark(session, job_id=payload.job_id, notes=payload.notes)
    return BookmarkResponse(
        id=b.id,
        job_id=b.job_id,
        notes=b.notes,
        bookmarked_at=b.bookmarked_at.isoformat(),
    )


@app.delete(
    "/api/v1/bookmarks/{job_id}",
    summary="Remove a bookmarked job",
)
def delete_bookmark(
    job_id: int,
    session: Session = Depends(get_db),
) -> dict[str, str]:
    """Remove bookmark for a job by job_id."""
    success = remove_bookmark(session, job_id=job_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Bookmark for job_id {job_id} not found.",
        )
    return {"message": f"Bookmark for job_id {job_id} removed successfully."}


@app.put(
    "/api/v1/bookmarks/{job_id}",
    response_model=BookmarkResponse,
    summary="Update bookmark notes",
)
def update_bookmark(
    job_id: int,
    payload: BookmarkNoteUpdate,
    session: Session = Depends(get_db),
) -> BookmarkResponse:
    """Update notes on an existing bookmark."""
    b = update_bookmark_notes(session, job_id=job_id, notes=payload.notes)
    if not b:
        raise HTTPException(
            status_code=404,
            detail=f"Bookmark for job_id {job_id} not found.",
        )
    return BookmarkResponse(
        id=b.id,
        job_id=b.job_id,
        notes=b.notes,
        bookmarked_at=b.bookmarked_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Salary Intelligence Endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/api/v1/salary/by-role",
    response_model=list[SalaryByRoleResponse],
    tags=["salary"],
    summary="Average salary stats by role",
)
def get_salary_by_role(
    currency: str = Query(default="USD", description="Currency filter (e.g. USD, EUR)"),
    limit: int = Query(default=20, ge=1, le=100, description="Max rows to return"),
    session: Session = Depends(get_db),
) -> list[SalaryByRoleResponse]:
    """Retrieve aggregated salary metrics grouped by job role."""
    rows = fetch_salary_by_role(session, currency=currency, limit=limit)
    return [SalaryByRoleResponse(**r) for r in rows]


@app.get(
    "/api/v1/salary/by-country",
    response_model=list[SalaryByCountryResponse],
    tags=["salary"],
    summary="Average salary stats by country",
)
def get_salary_by_country(
    currency: str = Query(default="USD", description="Currency filter (e.g. USD, EUR)"),
    limit: int = Query(default=20, ge=1, le=100, description="Max rows to return"),
    session: Session = Depends(get_db),
) -> list[SalaryByCountryResponse]:
    """Retrieve aggregated salary metrics grouped by country."""
    rows = fetch_salary_by_country(session, currency=currency, limit=limit)
    return [SalaryByCountryResponse(**r) for r in rows]


@app.get(
    "/api/v1/salary/currencies",
    response_model=list[str],
    tags=["salary"],
    summary="List available salary currencies",
)
def get_salary_currencies(session: Session = Depends(get_db)) -> list[str]:
    """Retrieve distinct currencies that exist in the salary dataset."""
    return fetch_available_salary_currencies(session)


# ---------------------------------------------------------------------------
# AI Recommendations Endpoint
# ---------------------------------------------------------------------------

@app.post(
    "/api/v1/ai/recommend",
    response_model=AIRecommendResponse,
    tags=["ai"],
    summary="AI-powered job recommendations",
)
def get_ai_job_recommendations(
    payload: AIRecommendRequest,
    session: Session = Depends(get_db),
) -> AIRecommendResponse:
    """Analyze a user resume or description and recommend the highest matching jobs."""
    result = ai_recommend_jobs(session, resume_text=payload.resume_text, top_n=payload.top_n)
    return AIRecommendResponse(
        ai_summary=result["ai_summary"],
        extracted_skills=result["extracted_skills"],
        recommended_roles=result["recommended_roles"],
        matched_jobs=[JobSummaryResponse(**j) for j in result["matched_jobs"]],
    )


# ---------------------------------------------------------------------------
# Email Alert Trigger Endpoint
# ---------------------------------------------------------------------------

@app.post(
    "/api/v1/subscriptions/trigger",
    response_model=AlertTriggerResponse,
    tags=["subscriptions"],
    summary="Trigger email alerts cycle",
)
def trigger_alerts(
    force: bool = Query(default=True, description="Force alert sending and bypass 23h limit"),
    session: Session = Depends(get_db),
) -> AlertTriggerResponse:
    """Manually dispatch digest email alerts to all active subscribers."""
    count = trigger_email_alerts(session, force=force)
    return AlertTriggerResponse(
        alerts_sent=count,
        message=f"Dispatched {count} job alerts successfully.",
    )


# ---------------------------------------------------------------------------
# Authentication Endpoints
# ---------------------------------------------------------------------------

@app.post(
    "/auth/register",
    response_model=TokenResponse,
    status_code=201,
    tags=["auth"],
    summary="Register a new user account",
)
def register(payload: UserRegister, session: Session = Depends(get_db)) -> TokenResponse:
    """Create a new user account and return a JWT access token."""
    from src.ingestion.db import User
    from src.serving.api.auth import hash_password, create_access_token

    # Check username uniqueness
    if session.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken.")
    # Check email uniqueness
    if session.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered.")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role="user",
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_access_token({"sub": str(user.id), "role": user.role, "username": user.username})
    return TokenResponse(access_token=token, role=user.role, username=user.username)


@app.post(
    "/auth/login",
    response_model=TokenResponse,
    tags=["auth"],
    summary="Login and receive a JWT access token",
)
def login(payload: UserLogin, session: Session = Depends(get_db)) -> TokenResponse:
    """Authenticate username + password and return a JWT access token."""
    from src.ingestion.db import User
    from src.serving.api.auth import verify_password, create_access_token

    user = session.query(User).filter(User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated. Contact an administrator.")

    token = create_access_token({"sub": str(user.id), "role": user.role, "username": user.username})
    return TokenResponse(access_token=token, role=user.role, username=user.username)


@app.get(
    "/auth/me",
    response_model=UserResponse,
    tags=["auth"],
    summary="Get current authenticated user profile",
)
def get_me(current_user=Depends(get_current_user)) -> UserResponse:
    """Return the profile of the currently authenticated user."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Admin-Only Endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/admin/users",
    response_model=list[UserResponse],
    tags=["admin"],
    summary="[Admin] List all registered users",
)
def admin_list_users(
    admin=Depends(require_admin),
    session: Session = Depends(get_db),
) -> list[UserResponse]:
    """Return all registered user accounts. Requires admin role."""
    from src.ingestion.db import User
    users = session.query(User).order_by(User.created_at.asc()).all()
    return [
        UserResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            role=u.role,
            is_active=u.is_active,
            created_at=u.created_at.isoformat(),
        )
        for u in users
    ]


@app.put(
    "/admin/users/{user_id}/role",
    response_model=UserResponse,
    tags=["admin"],
    summary="[Admin] Change a user's role",
)
def admin_update_role(
    user_id: int,
    payload: RoleUpdate,
    admin=Depends(require_admin),
    session: Session = Depends(get_db),
) -> UserResponse:
    """Update the role of a registered user. Requires admin role."""
    from src.ingestion.db import User
    if payload.role not in ("user", "admin"):
        raise HTTPException(status_code=400, detail="Role must be 'user' or 'admin'.")
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found.")
    user.role = payload.role
    session.commit()
    session.refresh(user)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@app.put(
    "/admin/users/{user_id}/toggle",
    response_model=UserResponse,
    tags=["admin"],
    summary="[Admin] Activate or deactivate a user",
)
def admin_toggle_user(
    user_id: int,
    admin=Depends(require_admin),
    session: Session = Depends(get_db),
) -> UserResponse:
    """Toggle the active status of a user account. Requires admin role."""
    from src.ingestion.db import User
    user = session.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found.")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Admins cannot deactivate themselves.")
    user.is_active = not user.is_active
    session.commit()
    session.refresh(user)
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )
