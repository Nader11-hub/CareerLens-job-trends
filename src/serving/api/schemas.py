from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """API health-check response."""

    status: str


class ErrorResponse(BaseModel):
    """Generic error envelope."""

    detail: str


class CountryTrendResponse(BaseModel):
    """Monthly job count for a single country."""

    country: str
    published_month: date
    job_count: int


class SkillTrendResponse(BaseModel):
    """Monthly job count for a single skill tag."""

    skill: str
    published_month: date
    job_count: int


class RoleTrendResponse(BaseModel):
    """Monthly job count for a single role title."""

    role: str
    published_month: date
    job_count: int


class TimeTrendResponse(BaseModel):
    """Overall monthly total job count."""

    published_month: date
    job_count: int


class JobSummaryResponse(BaseModel):
    """Lightweight summary of a single bronze job record."""

    id: int
    title: str
    company_name: str
    source: str
    country: str | None = None
    category: str | None = None
    job_type: str | None = None
    publication_date: str
    url: str
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    seniority: str | None = None
    match_score: int | None = None
    tags: list[str] | None = None


class SubscriptionCreate(BaseModel):
    """Schema to create or update an email subscription."""

    name: str = Field(..., min_length=1, max_length=120, description="Subscriber's name")
    email: str = Field(..., min_length=3, max_length=255, description="Valid email address")
    skills: list[str] = Field(default_factory=list, description="List of skills to match against")


class SubscriptionResponse(BaseModel):
    """Schema for subscription return responses."""

    id: int
    name: str
    email: str
    skills: list[str]
    active: bool
    created_at: str
    last_sent_at: str | None = None


class UnsubscribeRequest(BaseModel):
    """Schema to unsubscribe an email address."""

    email: str = Field(..., description="Email address to deactivate")


class StatsResponse(BaseModel):
    """High-level pipeline statistics surfaced from the database."""

    total_jobs: int = Field(description="Total validated jobs in the bronze layer.")
    total_dead_letters: int = Field(description="Unresolved dead-letter records.")
    sources: list[str] = Field(description="Distinct ingestion sources present.")
    earliest_job: date | None = Field(description="Earliest job publication date.")
    latest_job: date | None = Field(description="Most recent job publication date.")
    total_countries: int = Field(description="Distinct countries in the gold layer.")
    total_skills: int = Field(description="Distinct skills in the gold layer.")


class BookmarkCreate(BaseModel):
    """Schema for bookmarking a job posting."""

    job_id: int = Field(..., description="ID of the bronze-layer job to bookmark")
    notes: str | None = Field(default=None, max_length=1000, description="Optional personal notes")


class BookmarkResponse(BaseModel):
    """Schema returned when reading a bookmark."""

    id: int
    job_id: int
    notes: str | None = None
    bookmarked_at: str
    title: str | None = None
    company_name: str | None = None
    url: str | None = None
    source: str | None = None



class BookmarkNoteUpdate(BaseModel):
    """Schema to update the notes on an existing bookmark."""

    notes: str | None = Field(default=None, max_length=1000)


# ---------------------------------------------------------------------------
# Salary Intelligence schemas
# ---------------------------------------------------------------------------

class SalaryByRoleResponse(BaseModel):
    """Average salary stats aggregated per role."""

    role: str
    avg_salary: float
    min_salary: float
    max_salary: float
    job_count: int
    currency: str


class SalaryByCountryResponse(BaseModel):
    """Average salary stats aggregated per country."""

    country: str
    avg_salary: float
    min_salary: float
    max_salary: float
    job_count: int
    currency: str


# ---------------------------------------------------------------------------
# AI Recommendation schemas
# ---------------------------------------------------------------------------

class AIRecommendRequest(BaseModel):
    """Request payload for AI-powered job recommendations."""

    resume_text: str = Field(..., min_length=10, max_length=50000, description="User's skills or resume text")
    top_n: int = Field(default=10, ge=1, le=50, description="Number of job recommendations to return")


class AIRecommendResponse(BaseModel):
    """AI-generated job recommendation result."""

    ai_summary: str
    extracted_skills: list[str]
    recommended_roles: list[str]
    matched_jobs: list[JobSummaryResponse]


# ---------------------------------------------------------------------------
# Alert trigger schema
# ---------------------------------------------------------------------------

class AlertTriggerResponse(BaseModel):
    """Response for email alert trigger endpoint."""

    alerts_sent: int
    message: str
