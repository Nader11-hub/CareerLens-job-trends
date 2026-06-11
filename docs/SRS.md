# CareerLens — Software Requirements Specification (SRS)

**Version:** 1.0.0
**Date:** June 2026
**Status:** Final

---

## 1. Introduction

### 1.1 Purpose

This document specifies the functional and non-functional requirements for **CareerLens**, a production-oriented data engineering pipeline that ingests, processes, and visualises global remote job market trends. It serves as the primary technical reference for the graduation/internship project evaluation.

### 1.2 Scope

CareerLens is a self-contained data platform comprising:

- A **data ingestion layer** that fetches live job postings from external APIs and local fallback datasets.
- A **medallion transformation layer** (bronze → silver → gold) that normalises, enriches, and aggregates raw data.
- A **serving layer** exposing the processed data through a REST API and an interactive web dashboard.
- An **orchestration layer** that schedules and coordinates all pipeline stages.
- A **dead-letter handling subsystem** that captures, tracks, and retries invalid records.

### 1.3 Definitions & Acronyms

| Term | Definition |
|---|---|
| Bronze | Raw, validated records stored immediately after ingestion |
| Silver | Normalised and enriched records; analytics-ready grain |
| Gold | Aggregated metrics tables optimised for serving |
| Dead-letter | A record that failed validation during ingestion |
| Backfill | The process of retrying and promoting dead-letter records |
| Remotive | Primary live data source (Remotive.com remote jobs API) |
| Kaggle | Local CSV fallback dataset used during development |
| dbt | Data Build Tool — SQL-first transformation framework |

### 1.4 References

- Remotive API: https://remotive.com/api/remote-jobs
- FastAPI: https://fastapi.tiangolo.com
- Streamlit: https://streamlit.io
- dbt Core: https://docs.getdbt.com
- SQLAlchemy 2.0: https://docs.sqlalchemy.org

---

## 2. Overall Description

### 2.1 Product Perspective

CareerLens is a standalone data engineering platform. It has no upstream system dependencies beyond the Remotive public API and an optional Kaggle CSV. All components can be run locally via Python or deployed via Docker Compose.

### 2.2 Product Functions (Summary)

1. Fetch live remote job postings from Remotive (no API key required).
2. Fall back to a local Kaggle-style CSV when the live API is unavailable.
3. Validate each record against a strict schema; route invalid records to a dead-letter table.
4. Transform raw bronze data into analytics-ready silver and gold tables.
5. Retry failed dead-letter records on a configurable schedule.
6. Expose gold-layer data through a versioned REST API.
7. Visualise trends on a dark-themed interactive dashboard.
8. Run the full pipeline on a recurring schedule or on demand.

### 2.3 User Classes

| Class | Description |
|---|---|
| Data Analyst | Consumes the dashboard and API to explore trends |
| Data Engineer | Operates and extends the pipeline |
| Evaluator | Reviews code quality, architecture, and tests |

### 2.4 Operating Environment

- Python 3.11+
- PostgreSQL 16 (production) / SQLite (local tests)
- Docker Engine 24+ / Docker Compose v2
- GitHub Actions (CI/CD)

### 2.5 Assumptions and Dependencies

- The Remotive API is publicly accessible with no authentication.
- The Kaggle fallback CSV is present at `data/fallback/kaggle_fallback.csv` when needed.
- PostgreSQL is the database backend for production; SQLite is used for unit tests.
- Public schema usage in PostgreSQL is acceptable for the project scope.

---

## 3. Functional Requirements

### 3.1 Data Ingestion

| ID | Requirement |
|---|---|
| FR-01 | The system SHALL fetch job postings from `https://remotive.com/api/remote-jobs` on each pipeline run. |
| FR-02 | The system SHALL support an optional `category` query parameter to filter the Remotive response. |
| FR-03 | The system SHALL retry failed Remotive API requests up to 3 times with exponential back-off (2 s → 8 s). |
| FR-04 | The system SHALL automatically activate the Kaggle fallback CSV when the Remotive API is unavailable. |
| FR-05 | The system SHALL validate each fetched record against the `JobRecord` Pydantic schema before persistence. |
| FR-06 | The system SHALL write validated records to the `bronze_jobs` table using upsert semantics (idempotent). |
| FR-07 | The system SHALL write invalid records to the `bronze_jobs_dead_letter` table with the error message and source. |

### 3.2 Transformation

| ID | Requirement |
|---|---|
| FR-08 | The system SHALL transform `bronze_jobs` into `silver_jobs` by normalising country, role, and date-grain fields. |
| FR-09 | The system SHALL produce four gold tables: `gold_country_trends`, `gold_skill_trends`, `gold_role_trends`, `gold_time_trends`. |
| FR-10 | The transformation layer SHALL support both a Python runner (for local/SQLite) and dbt models (for PostgreSQL). |
| FR-11 | All dbt models SHALL have schema tests (`not_null`, `unique`, `accepted_values`) defined in `schema.yml` files. |

### 3.3 Dead-Letter Backfill

| ID | Requirement |
|---|---|
| FR-12 | The system SHALL provide a backfill process that retries all unresolved dead-letter records. |
| FR-13 | The backfill process SHALL apply sanitisation rules (e.g. URL prefix repair) before re-validation. |
| FR-14 | Successfully re-validated records SHALL be promoted to `bronze_jobs` and marked resolved. |
| FR-15 | Records that still fail after sanitisation SHALL have their `retry_count` incremented and remain unresolved. |
| FR-16 | A standalone `backfill_cli.py` SHALL provide a `--dry-run` mode that shows recovery status without writing. |

### 3.4 REST API

| ID | Requirement |
|---|---|
| FR-17 | The API SHALL expose `GET /health` for liveness checks. |
| FR-18 | The API SHALL expose `GET /api/v1/stats` returning pipeline-level KPIs. |
| FR-19 | The API SHALL expose `GET /api/v1/trends/countries` with `limit`, `month`, and `country` filter params. |
| FR-20 | The API SHALL expose `GET /api/v1/trends/skills` with `limit`, `month`, and `skill` filter params. |
| FR-21 | The API SHALL expose `GET /api/v1/trends/roles` with `limit`, `month`, and `role` filter params. |
| FR-22 | The API SHALL expose `GET /api/v1/trends/time` with a `limit` param. |
| FR-23 | The API SHALL expose `GET /api/v1/jobs` with `page`, `page_size`, and `source` params for bronze browsing. |
| FR-24 | The API SHALL serve OpenAPI documentation at `/docs`. |
| FR-25 | The API SHALL include CORS headers allowing cross-origin requests. |

### 3.5 Dashboard

| ID | Requirement |
|---|---|
| FR-26 | The dashboard SHALL display a KPI bar with total jobs, countries, skills, and date range. |
| FR-27 | The dashboard SHALL render a choropleth world map of total jobs by country. |
| FR-28 | The dashboard SHALL render a skills treemap for the top 40 skills. |
| FR-29 | The dashboard SHALL render a role demand horizontal bar chart. |
| FR-30 | The dashboard SHALL render a time-series area chart of total monthly job counts. |
| FR-31 | The dashboard SHALL provide a sidebar with a Top-N filter slider. |
| FR-32 | The dashboard SHALL support a job browse page with text search and source filter. |

### 3.6 Orchestration

| ID | Requirement |
|---|---|
| FR-33 | The pipeline runner SHALL execute ingestion, transformation, and backfill in sequence. |
| FR-34 | The scheduler SHALL run the pipeline on a configurable interval (minutes). |
| FR-35 | The scheduler SHALL execute an initial pipeline run immediately on startup. |
| FR-36 | The scheduler SHALL handle SIGTERM and SIGINT signals with graceful shutdown. |

---

## 4. Non-Functional Requirements

### 4.1 Reliability

- NFR-01: The pipeline SHALL recover gracefully from Remotive API failures via the fallback mechanism (FR-04).
- NFR-02: The dead-letter mechanism SHALL ensure no record is silently dropped.
- NFR-03: All database writes SHALL use transactions; failures SHALL trigger rollback and error reporting.

### 4.2 Performance

- NFR-04: A full pipeline run on the Remotive dataset (≤ 500 jobs) SHALL complete within 60 seconds.
- NFR-05: API endpoints SHALL respond within 500 ms at p95 on a single-core server with ≤ 50,000 gold rows.

### 4.3 Maintainability

- NFR-06: All Python modules SHALL have type hints on public functions and classes.
- NFR-07: All public functions SHALL have Google-style docstrings.
- NFR-08: Code style SHALL conform to `black` (100-char line length) and `ruff` lint rules.
- NFR-09: All business logic SHALL be covered by automated tests (target: > 80% branch coverage).

### 4.4 Security

- NFR-10: No secrets or credentials SHALL be hardcoded; all are read from environment variables or `.env`.
- NFR-11: The Docker runtime image SHALL run as a non-root user.

### 4.5 Portability

- NFR-12: The system SHALL run locally using Python 3.11+ without Docker.
- NFR-13: The system SHALL deploy via `docker compose up --build` with no manual setup steps.
- NFR-14: Unit tests SHALL use an in-memory SQLite database requiring no external dependencies.

---

## 5. Acceptance Criteria

| Criterion | Verification Method |
|---|---|
| All tests pass | `pytest` exits 0 |
| No lint violations | `ruff check .` exits 0 |
| No formatting violations | `black --check .` exits 0 |
| API `/health` returns `{"status": "ok"}` | Manual curl / test |
| Dashboard loads with data after a pipeline run | Manual browser check |
| Dead-letter records are persisted for invalid inputs | Unit test assertion |
| Backfill promotes recoverable dead-letters | Unit test assertion |
| Docker Compose stack starts all 4 services | `docker compose ps` |
| CI pipeline passes on GitHub | GitHub Actions green |
