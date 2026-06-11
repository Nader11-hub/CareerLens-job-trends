"""Script to generate a large, realistic fallback dataset with thousands of jobs."""

from __future__ import annotations

import csv
import random
from datetime import datetime, timedelta, UTC
from pathlib import Path

from src.config import settings
from src.logger import logger

ROLES = [
    ("Data Engineer", "Data Engineering", ["python", "sql", "aws", "spark", "airflow"]),
    ("Senior Data Engineer", "Data Engineering", ["python", "sql", "snowflake", "dbt", "spark"]),
    ("Analytics Engineer", "Data Engineering", ["sql", "dbt", "snowflake", "looker"]),
    ("Python Developer", "Software Development", ["python", "django", "postgresql", "docker"]),
    ("Backend Engineer", "Software Development", ["python", "fastapi", "postgresql", "aws"]),
    ("Machine Learning Engineer", "AI & Machine Learning", ["python", "pytorch", "tensorflow", "mlflow"]),
    ("AI Research Scientist", "AI & Machine Learning", ["python", "pytorch", "scikit-learn"]),
    ("Data Analyst", "Data Analytics", ["sql", "excel", "tableau", "powerbi"]),
    ("Senior Data Analyst", "Data Analytics", ["sql", "python", "tableau", "excel"]),
    ("DevOps Engineer", "Software Development", ["aws", "terraform", "kubernetes", "docker", "ci/cd"]),
    ("Fullstack Developer", "Software Development", ["javascript", "react", "nextjs", "node.js", "postgresql"]),
]

COMPANIES = [
    "TechCorp",
    "DataFlow",
    "CloudScale",
    "AI Innovations",
    "GraphQube",
    "PyStudio",
    "ByteSize",
    "LogiTech",
    "FintechLabs",
    "WebFlow",
    "AeroSpace",
    "MedTech",
    "EduLearn",
    "GlobalSync",
    "CodeFactory",
    "ApexSystems",
    "CoreData",
    "NextGen",
    "QuantumCompute",
    "InfinitySoft",
]

LOCATIONS = [
    "Worldwide",
    "Global",
    "USA",
    "Canada",
    "UK",
    "Germany",
    "France",
    "Berlin, Germany",
    "London, UK",
    "New York, USA",
    "San Francisco, USA",
    "Toronto, Canada",
    "Paris, France",
    "Tokyo, Japan",
    "Sydney, Australia",
]

SALARIES = [
    "$120,000 - $140,000",
    "$90,000 - $110,000",
    "$150,000 - $180,000",
    "$70,000 - $90,000",
    "$100,000 - $120,000",
    None,
]


def generate_fallback_dataset(output_path: Path, count: int = 25000) -> None:
    """Generate a realistic mock CSV dataset with specified job count.

    Args:
        output_path: Path where the CSV will be written.
        count: Number of job postings to generate.
    """
    logger.info("Generating fallback dataset with %d jobs at: %s", count, output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    base_time = datetime(2026, 6, 11, 12, 0, 0, tzinfo=UTC)

    fieldnames = [
        "id",
        "url",
        "title",
        "company_name",
        "company_logo",
        "category",
        "tags",
        "job_type",
        "publication_date",
        "candidate_required_location",
        "salary",
        "description",
    ]

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for i in range(1, count + 1):
            role_info = random.choice(ROLES)
            title, category, tags = role_info
            company = random.choice(COMPANIES)
            location = random.choice(LOCATIONS)
            salary = random.choice(SALARIES)
            job_id = 1000 + i

            # Spread dates over the last 180 days to populate trends
            days_ago = random.randint(0, 180)
            seconds_offset = random.randint(0, 86400)
            pub_date = base_time - timedelta(days=days_ago, seconds=seconds_offset)

            # Build a job row
            row = {
                "id": job_id,
                "url": f"https://example.com/jobs/{job_id}",
                "title": title,
                "company_name": company,
                "company_logo": f"https://logo.com/{random.randint(1, 20)}",
                "category": category,
                "tags": str(tags),
                "job_type": "full_time" if random.random() > 0.15 else "part_time",
                "publication_date": pub_date.isoformat(),
                "candidate_required_location": location,
                "salary": salary,
                "description": f"Exciting opportunity for a {title} at {company}. Join our remote team!",
            }
            writer.writerow(row)

    logger.info("Successfully generated %d fallback jobs.", count)


if __name__ == "__main__":
    generate_fallback_dataset(settings.fallback_dataset_path, 25000)
