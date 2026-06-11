from __future__ import annotations

import ast
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_text(value: Any) -> str | None:
    """Normalize string-like values by trimming whitespace and null-equivalents."""

    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return str(value).strip() or None


class JobRecord(BaseModel):
    """Canonical job posting model used across ingestion and backfill."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    id: int = Field(..., gt=0)
    url: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    company_name: str = Field(..., min_length=1)
    company_logo: str | None = None
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    job_type: str | None = None
    publication_date: datetime
    candidate_required_location: str | None = None
    salary: str | None = None
    description: str | None = None
    source: str = Field(default="remotive")

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        """Require HTTP(S) URLs for source job links."""

        if not value.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return value

    @field_validator("title", "company_name", mode="before")
    @classmethod
    def validate_required_text(cls, value: Any) -> str:
        """Ensure required text fields are not empty after trimming."""

        normalized = _normalize_text(value)
        if normalized is None:
            raise ValueError("value cannot be blank")
        return normalized

    @field_validator(
        "company_logo",
        "category",
        "job_type",
        "candidate_required_location",
        "salary",
        "description",
        "source",
        mode="before",
    )
    @classmethod
    def normalize_optional_text(cls, value: Any) -> str | None:
        """Trim optional text fields and collapse blank values to None."""

        return _normalize_text(value)

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value: Any) -> list[str]:
        """Normalize tags from list, CSV, or Python-list string formats."""

        if value in (None, "", []):
            return []

        raw_tags: list[str]
        if isinstance(value, list):
            raw_tags = [str(item) for item in value]
        elif isinstance(value, str):
            candidate = value.strip()
            if not candidate:
                return []
            if candidate.startswith("[") and candidate.endswith("]"):
                try:
                    parsed = ast.literal_eval(candidate)
                except (SyntaxError, ValueError):
                    parsed = candidate.strip("[]").split(",")
                if isinstance(parsed, list):
                    raw_tags = [str(item) for item in parsed]
                else:
                    raw_tags = [str(parsed)]
            else:
                raw_tags = candidate.split(",")
        else:
            raw_tags = [str(value)]

        normalized = []
        seen = set()
        for item in raw_tags:
            tag = item.strip().lower()
            if tag and tag not in seen:
                seen.add(tag)
                normalized.append(tag)
        return normalized

    @field_validator("publication_date", mode="before")
    @classmethod
    def normalize_publication_date(cls, value: Any) -> datetime:
        """Parse string or naive datetimes into timezone-aware UTC datetimes."""

        if isinstance(value, datetime):
            dt = value
        elif isinstance(value, str):
            normalized = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
        else:
            raise ValueError("publication_date must be a valid ISO datetime")

        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)

    def to_bronze_dict(self) -> dict[str, Any]:
        """Serialize the record for bronze-layer persistence."""

        return self.model_dump()
