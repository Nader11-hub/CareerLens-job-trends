"""CareerLens job fetchers.

Provides fetch functions for all supported data sources:
  - Remotive API (all categories)
  - RemoteOK public API (no auth)
  - Arbeitnow public API (no auth, paginated)
  - Kaggle local CSV fallback

The ``fetch_all_sources()`` function runs all three live APIs in parallel and
returns a deduplicated merged list — enabling thousands of jobs per run.
"""

from __future__ import annotations

import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import settings
from src.logger import logger

# ---------------------------------------------------------------------------
# Retry policy: 3 attempts, 2 → 8 s back-off, log before each sleep
# ---------------------------------------------------------------------------
_RETRY = retry(
    retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=8),
    before_sleep=before_sleep_log(logger, 20),
    reraise=True,
)


@_RETRY
def _get(url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> requests.Response:
    """Shared HTTP GET with retry."""
    return requests.get(url, params=params or {}, timeout=30, **kwargs)


# ---------------------------------------------------------------------------
# Remotive
# ---------------------------------------------------------------------------

def fetch_from_remotive_api(
    url: str | None = None,
    category: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Fetch remote jobs from the live Remotive API.

    Args:
        url: Override the base API URL (defaults to ``settings.remotive_api_url``).
        category: Optional job category filter passed as a query parameter.
        limit: Maximum number of jobs to return (applied client-side when set).

    Returns:
        A list of raw job dictionaries as returned by the API.

    Raises:
        requests.HTTPError: If the API returns a non-2xx status after retries.
    """
    api_url = url or settings.remotive_api_url
    params: dict[str, Any] = {}
    if category:
        params["category"] = category

    logger.info("Fetching jobs from Remotive API: %s  params=%s", api_url, params)
    response = _get(api_url, params)
    response.raise_for_status()

    payload = response.json()
    jobs: list[dict[str, Any]] = payload.get("jobs", [])
    if limit is not None:
        jobs = jobs[:limit]

    logger.info(
        "Remotive API response: %s jobs fetched (job-count header=%s)",
        len(jobs),
        payload.get("job-count", "n/a"),
    )
    return jobs


def fetch_from_remotive_all_categories() -> list[dict[str, Any]]:
    """Fetch jobs from every Remotive category and merge, deduplicating by id.

    Returns:
        Deduplicated list of raw job dicts from all Remotive categories.
    """
    categories_url = settings.remotive_api_url.rstrip("/") + "/categories"
    try:
        resp = _get(categories_url)
        resp.raise_for_status()
        categories: list[str] = [c["name"] for c in resp.json().get("jobs", [])]
        logger.info("Remotive: found %d categories", len(categories))
    except Exception as exc:
        logger.warning("Could not fetch Remotive categories (%s) — using uncategorised only", exc)
        return fetch_from_remotive_api()

    seen_ids: set[int] = set()
    all_jobs: list[dict[str, Any]] = []

    for job in fetch_from_remotive_api():
        jid = job.get("id")
        if jid and jid not in seen_ids:
            seen_ids.add(jid)
            all_jobs.append(job)

    for cat in categories:
        try:
            for job in fetch_from_remotive_api(category=cat):
                jid = job.get("id")
                if jid and jid not in seen_ids:
                    seen_ids.add(jid)
                    all_jobs.append(job)
        except Exception as exc:
            logger.warning("Remotive category '%s' failed: %s", cat, exc)

    logger.info("Remotive all-categories total: %d unique jobs", len(all_jobs))
    return all_jobs


# ---------------------------------------------------------------------------
# RemoteOK
# ---------------------------------------------------------------------------

def fetch_from_remoteok() -> list[dict[str, Any]]:
    """Fetch remote jobs from the RemoteOK public API (no auth required).

    RemoteOK returns a JSON array; the first element is a legal disclaimer —
    we skip it. IDs are hashed into a non-colliding namespace above Remotive's.

    Returns:
        A list of normalised job dicts compatible with ``JobRecord``.
    """
    url = "https://remoteok.com/api"
    logger.info("Fetching jobs from RemoteOK API: %s", url)
    try:
        resp = requests.get(url, headers={"User-Agent": "CareerLens/1.0"}, timeout=30)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("RemoteOK fetch failed: %s", exc)
        return []

    raw: list[Any] = resp.json()
    jobs_raw = [item for item in raw if isinstance(item, dict) and item.get("id")]

    normalised: list[dict[str, Any]] = []
    for job in jobs_raw:
        try:
            raw_id = int(str(job["id"]).lstrip("r"))
        except (ValueError, KeyError):
            continue

        # Stable positive integer ID in RemoteOK namespace (500M–1.5B)
        stable_id = abs(hash(f"remoteok:{raw_id}")) % 1_000_000_000 + 500_000_000

        tags_raw: list[str] = job.get("tags") or []
        if isinstance(tags_raw, str):
            tags_raw = [t.strip() for t in tags_raw.split(",") if t.strip()]

        pub_date = job.get("date") or job.get("epoch")
        if isinstance(pub_date, (int, float)):
            pub_date = datetime.fromtimestamp(pub_date, tz=UTC).isoformat()
        elif not pub_date:
            pub_date = "2024-01-01T00:00:00+00:00"

        normalised.append({
            "id": stable_id,
            "url": job.get("url") or f"https://remoteok.com/remote-jobs/{raw_id}",
            "title": job.get("position") or job.get("title") or "Unknown Role",
            "company_name": job.get("company") or "Unknown Company",
            "company_logo": job.get("company_logo"),
            "category": tags_raw[0] if tags_raw else None,
            "tags": tags_raw,
            "job_type": "full_time",
            "publication_date": pub_date,
            "candidate_required_location": job.get("location") or "Worldwide",
            "salary": job.get("salary"),
            "description": job.get("description"),
            "source": "remoteok",
        })

    logger.info("RemoteOK: %d jobs normalised", len(normalised))
    return normalised


# ---------------------------------------------------------------------------
# Arbeitnow
# ---------------------------------------------------------------------------

def fetch_from_arbeitnow(max_pages: int = 10) -> list[dict[str, Any]]:
    """Fetch remote jobs from the Arbeitnow public job-board API (no auth required).

    Paginates up to ``max_pages`` pages (~50 jobs each) for up to 500 jobs.
    IDs are hashed into a non-colliding namespace above 1.5B.

    Args:
        max_pages: Maximum number of pages to fetch (default 10 → ~500 jobs).

    Returns:
        A list of normalised job dicts compatible with ``JobRecord``.
    """
    base_url = "https://www.arbeitnow.com/api/job-board-api"
    logger.info("Fetching jobs from Arbeitnow API: %s", base_url)
    all_raw: list[dict[str, Any]] = []

    for page in range(1, max_pages + 1):
        try:
            resp = requests.get(base_url, params={"page": page}, timeout=30)
            resp.raise_for_status()
            page_jobs: list[dict[str, Any]] = resp.json().get("data", [])
            if not page_jobs:
                break
            all_raw.extend(page_jobs)
            logger.info("Arbeitnow page %d: %d jobs", page, len(page_jobs))
        except Exception as exc:
            logger.warning("Arbeitnow page %d failed: %s", page, exc)
            break

    normalised: list[dict[str, Any]] = []
    for job in all_raw:
        slug = job.get("slug") or job.get("title", "unknown")
        # Stable positive integer ID in Arbeitnow namespace (1.5B–2.5B)
        stable_id = abs(hash(f"arbeitnow:{slug}")) % 1_000_000_000 + 1_500_000_000

        tags_raw: list[str] = job.get("tags") or []
        if isinstance(tags_raw, str):
            tags_raw = [t.strip() for t in tags_raw.split(",") if t.strip()]

        pub_date = job.get("created_at")
        if isinstance(pub_date, (int, float)):
            pub_date = datetime.fromtimestamp(pub_date, tz=UTC).isoformat()
        elif not pub_date:
            pub_date = "2024-01-01T00:00:00+00:00"

        location = job.get("location") or ("Remote" if job.get("remote") else "Worldwide")
        job_types: list[str] = job.get("job_types") or ["full_time"]

        normalised.append({
            "id": stable_id,
            "url": job.get("url") or f"https://www.arbeitnow.com/jobs/{slug}",
            "title": job.get("title") or "Unknown Role",
            "company_name": job.get("company_name") or "Unknown Company",
            "company_logo": job.get("company_logo"),
            "category": tags_raw[0] if tags_raw else None,
            "tags": tags_raw,
            "job_type": job_types[0] if job_types else "full_time",
            "publication_date": pub_date,
            "candidate_required_location": location,
            "salary": None,
            "description": job.get("description"),
            "source": "arbeitnow",
        })

    logger.info("Arbeitnow: %d jobs normalised", len(normalised))
    return normalised


# ---------------------------------------------------------------------------
# Kaggle fallback (local CSV seed)
# ---------------------------------------------------------------------------

def fetch_from_kaggle_fallback(csv_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Load the local fallback dataset used for development and resilience.

    Args:
        csv_path: Path to the CSV file. Defaults to ``settings.fallback_dataset_path``.

    Returns:
        A list of raw job dictionaries parsed from the CSV.

    Raises:
        FileNotFoundError: If the CSV file does not exist at the resolved path.
    """
    path = Path(csv_path) if csv_path else settings.fallback_dataset_path
    if not path.is_absolute():
        path = (settings.fallback_dataset_path.parent.parent / path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Fallback CSV file not found at {path}")

    logger.info("Loading fallback dataset from %s", path)
    jobs: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row["id"] = int(row["id"]) if row.get("id") else None
            jobs.append(row)

    logger.info("Loaded %s jobs from Kaggle fallback dataset.", len(jobs))
    return jobs


# ---------------------------------------------------------------------------
# Aggregate: all live sources in parallel
# ---------------------------------------------------------------------------

def fetch_all_sources() -> list[dict[str, Any]]:
    """Fetch from Remotive (all categories), RemoteOK, and Arbeitnow in parallel.

    Runs all three APIs concurrently using a thread pool, then deduplicates
    by job URL so overlapping listings are not double-counted.

    Returns:
        Merged, deduplicated list of raw normalised job dicts from all sources.
    """
    source_fns = {
        "remotive": fetch_from_remotive_all_categories,
        "remoteok": fetch_from_remoteok,
        "arbeitnow": fetch_from_arbeitnow,
    }

    results: dict[str, list[dict[str, Any]]] = {k: [] for k in source_fns}
    with ThreadPoolExecutor(max_workers=3) as pool:
        future_to_name = {pool.submit(fn): name for name, fn in source_fns.items()}
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                results[name] = future.result()
            except Exception as exc:
                logger.warning("Source '%s' failed in parallel fetch: %s", name, exc)

    seen_urls: set[str] = set()
    merged: list[dict[str, Any]] = []
    for name in ("remotive", "remoteok", "arbeitnow"):
        for job in results[name]:
            url = job.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                merged.append(job)

    logger.info(
        "fetch_all_sources: remotive=%d  remoteok=%d  arbeitnow=%d  → total_unique=%d",
        len(results["remotive"]),
        len(results["remoteok"]),
        len(results["arbeitnow"]),
        len(merged),
    )
    return merged
