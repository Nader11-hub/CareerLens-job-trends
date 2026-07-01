from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Environment-driven application settings."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    log_dir: str = Field(default="logs")
    log_file: str = Field(default="careerlens.log")

    mysql_user: str = Field(default="root")
    mysql_password: str = Field(default="")
    mysql_db: str = Field(default="careerlens")
    mysql_host: str = Field(default="localhost")
    mysql_port: int = Field(default=3306)
    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")

    remotive_api_url: str = Field(default="https://remotive.com/api/remote-jobs")
    kaggle_fallback_path: str = Field(default="data/fallback/kaggle_fallback.csv")

    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000)
    api_base_url: str = Field(default="http://localhost:8000")

    bronze_schema: str = Field(default="public")
    silver_schema: str = Field(default="public")
    gold_schema: str = Field(default="public")

    # Near-real-time scheduling: how often the scheduler pipeline re-runs.
    # Intentionally a short-interval batch pipeline (not streaming).
    pipeline_interval_minutes: int = Field(default=5)

    # Email / SMTP settings for daily job alert digests
    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    smtp_from_name: str = Field(default="CareerLens Alerts")

    # JSearch / RapidAPI settings for 4th live job source
    # Get a free key at https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
    # Leave JSEARCH_API_KEY empty to disable this source gracefully
    jsearch_api_key: str = Field(default="")
    jsearch_api_url: str = Field(default="https://jsearch.p.rapidapi.com/search")

    # Google Gemini API key for AI-powered job recommendations
    # Get a free key at https://aistudio.google.com/app/apikey
    gemini_api_key: str = Field(default="")


    @computed_field
    @property
    def database_url(self) -> str:
        """Build the SQLAlchemy-compatible database URL."""
        if self.database_url_override:
            return self.database_url_override
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}"
            f"?charset=utf8mb4"
        )

    @computed_field
    @property
    def logs_path(self) -> Path:
        """Return the absolute log directory path."""
        return PROJECT_ROOT / self.log_dir

    @computed_field
    @property
    def fallback_dataset_path(self) -> Path:
        """Return the absolute fallback dataset path."""
        return (PROJECT_ROOT / self.kaggle_fallback_path).resolve()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings object."""
    return Settings()


settings = get_settings()
