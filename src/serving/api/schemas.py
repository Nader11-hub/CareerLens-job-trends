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


class StatsResponse(BaseModel):
    """High-level pipeline statistics surfaced from the database."""

    total_jobs: int = Field(description="Total validated jobs in the bronze layer.")
    total_dead_letters: int = Field(description="Unresolved dead-letter records.")
    sources: list[str] = Field(description="Distinct ingestion sources present.")
    earliest_job: date | None = Field(description="Earliest job publication date.")
    latest_job: date | None = Field(description="Most recent job publication date.")
    total_countries: int = Field(description="Distinct countries in the gold layer.")
    total_skills: int = Field(description="Distinct skills in the gold layer.")
