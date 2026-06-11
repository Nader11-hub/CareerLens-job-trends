# 🌐 CareerLens: Global Job Market Trends Pipeline

[![CI Status](https://img.shields.io/badge/CI-passing-success?style=flat-square)](#)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue?style=flat-square)](#)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.36+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![dbt Core](https://img.shields.io/badge/dbt--core-1.8+-FF694B?style=flat-square&logo=dbt&logoColor=white)](https://docs.getdbt.com)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat-square)](https://github.com/psf/black)
[![Linter](https://img.shields.io/badge/linter-ruff-d7ff00?style=flat-square)](https://github.com/astral-sh/ruff)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](#)

CareerLens is a production-grade data engineering pipeline designed to ingest, transform, and serve global remote job market insights. It features a robust **Medallion Architecture** (Bronze ➡️ Silver ➡️ Gold), resilient dead-letter handling with a retry-and-promote backfill loop, clean type safety (via Pydantic), automated test coverage, and premium serving layers (FastAPI + Streamlit).

Designed as an end-to-end portfolio and graduation-quality project, it shows how to build pipelines with local SQLite/Postgres backends, automate transformations using **dbt**, and deploy multi-container environments with Docker Compose.

---

## 🏗️ Architecture Overview

The pipeline implements the **Medallion Architecture** pattern, moving data through increasingly refined quality zones:

```
                  ┌──────────────────────┐
                  │ 🌐 Live Remotive API │
                  └──────────┬───────────┘
                             │ (HTTP GET with Tenacity Retries)
                             ▼
                  ┌──────────────────────┐      (API Offline)
                  │   Ingestion Engine   │ ◄──────────────────┐
                  └──────────┬───────────┘                    │
                             │                                │
                  ┌──────────┴───────────┐         ┌──────────┴───────────┐
                  │ Pydantic Validation  │         │  Local Kaggle Seed   │
                  └────┬────────────┬────┘         └──────────────────────┘
                       │            │
             (Valid)   │            │ (Invalid)
                       ▼            ▼
   ┌───────────────────┐    ┌───────────────────────────┐
   │ 🥉 Bronze Jobs    │    │ ❌ Dead-Letter Table      │
   │   (Raw Valid)     │    │   (Invalid + Retry Metadata)
   └─────────┬─────────┘    └─────────────┬─────────────┘
             │                            │
             │ (Python Run / dbt)         │ (Manual / Scheduled)
             ▼                            ▼
   ┌───────────────────┐    ┌───────────────────────────┐
   │ 🥈 Silver Jobs    │◄───┤  Sanitized Backfill Loop  │
   │  (Normalized Data)│    └───────────────────────────┘
   └─────────┬─────────┘
             ├──────────────────────┬──────────────────────┐
             ▼                      ▼                      ▼
   ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
   │ 🥇 Country Trends │  │ 🥇 Skill Trends   │  │ 🥇 Role Trends    │
   └─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘
             │                      │                      │
             └──────────────────────┼──────────────────────┘
                                    ▼
                        ┌──────────────────────┐
                        │   FastAPI REST API   │
                        └──────────┬───────────┘
                                   │ (JSON Endpoints)
                                   ▼
                        ┌──────────────────────┐
                        │ Streamlit Dashboard  │
                        └──────────────────────┘
```

For more details on schemas and data formats, see the [Data Model Documentation](docs/data-model.md). For system specifications and requirements, see the [Software Requirements Specification (SRS)](docs/SRS.md).

---

## ⏱️ Real-Time Behavior

CareerLens is designed as a **near-real-time batch pipeline**, not a streaming system. This is an intentional architectural choice:

| Layer | Behavior |
|---|---|
| **Pipeline** | Batch run on a configurable interval (default: **5 min**) |
| **Dashboard cache** | Data re-fetched from the API every **60 seconds** |
| **Auto-refresh** | Toggle in the sidebar refreshes the page every **60 s** |
| **"Last updated" stamp** | Sidebar shows `HH:MM:SS` of the last page render |

### Why not true streaming?

Job postings update on the **order of hours**, not seconds. A 5-minute polling cycle already captures new listings well within the natural update cadence of sources like Remotive. True streaming infrastructure (Kafka, Flink, etc.) would add significant operational complexity with no meaningful benefit for this data pattern.

### Configuring the interval

Set `PIPELINE_INTERVAL_MINUTES` in your `.env` file (or as a Docker environment variable) to change the schedule without editing any code:

```bash
# .env — demo / development
PIPELINE_INTERVAL_MINUTES=5

# .env — production (reduce API load)
PIPELINE_INTERVAL_Second=60
```

The `--schedule-interval` CLI flag on `src.orchestration.runner` overrides this value for one-off runs.

> [!NOTE]
> **Production Consideration for Auto-Refresh**: In local demonstration, we use `time.sleep(60)` inside the Streamlit script to trigger auto-refreshes. For production deployments, this is a known anti-pattern as it blocks the main execution thread. A production-ready setup should replace this with the asynchronous, non-blocking `streamlit-autorefresh` component.

---

## 📂 Repository Layout

```
job-trends-pipeline/
├── .github/workflows/       # GitHub Actions CI configurations (lint, test, build)
├── data/                    # Fallback dataset storage (Kaggle CSV seed)
├── docs/                    # Requirements, data models, Diagrams (Mermaid) & Contributing
│   ├── diagrams/            # Architecture & medallion flow source files
│   ├── CONTRIBUTING.md      # Development setup & contributor guidelines
│   ├── data-model.md        # Table definitions, lineage & ER diagrams
│   └── SRS.md               # Software Requirements Specification
├── src/                     # Application source code
│   ├── ingestion/           # Ingestion scripts (fetching, validation, db, backfill)
│   ├── serving/             # Serving layer: FastAPI REST API & Streamlit Dashboard
│   │   ├── api/             # FastAPI routers, endpoints, dependency injection, service helpers
│   │   └── dashboard/       # Streamlit visual charts, custom theme, and pages
│   ├── transformation/      # Transformation layer: Python runner & dbt project folder
│   │   └── models/          # dbt SQL models for Silver and Gold tables
│   └── orchestration/       # Task runner CLI & APScheduler scheduler daemon
├── tests/                   # Test suite (unit, mock, integration, and e2e)
├── Dockerfile               # Multi-stage container file
├── docker-compose.yml       # Docker Compose multi-service topology
└── requirements.txt         # Project dependencies
```

---

## ⚙️ Quick Start (Local Development)

### 1. Set Up Environment
Create a virtual environment, install requirements, and set up your `.env` file:
```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

### 2. Run the Ingestion & Transformation
You can execute a single run of the pipeline using SQLite:
```bash
# Run using the live Remotive API
python -m src.orchestration.runner --source remotive

# Run using the local Kaggle CSV backup dataset
python -m src.orchestration.runner --source kaggle
```

### 3. Start the FastAPI API Server
Launch the API using `uvicorn`:
```bash
uvicorn src.serving.api.main:app --reload
```
- Interactive OpenAPI docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- API JSON Schema: [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

### 4. Start the Streamlit Dashboard
Launch the dashboard:
```bash
streamlit run src/serving/dashboard/app.py
```
View the dashboard at [http://localhost:8501](http://localhost:8501) (includes filters, global heatmap, skill treemap, and paginated job browser).

---

## 🐳 Docker Compose Deployment

The stack is packaged into a hardened multi-container Docker Compose file (`docker-compose.yml`). To spin up PostgreSQL, the FastAPI backend, the Streamlit frontend, and the scheduler daemon:

```bash
docker compose up --build
```

### Services Available
- **Postgres Database**: `localhost:5432`
- **FastAPI Core REST API**: `http://localhost:8000` (incorporates health checks and automatic startup migrations)
- **Streamlit Analytics Dashboard**: `http://localhost:8501` (waits for the API health check to pass; auto-refreshes every 60 s and shows a **"Last updated"** timestamp in the sidebar)
- **Scheduler (APScheduler Daemon)**: Runs in the background, executing the ingestion, dbt models, and backfill steps on a **configurable interval** (default: **5 min**, set via `PIPELINE_INTERVAL_MINUTES`). This is a near-real-time batch pipeline — see [Real-Time Behavior](#%EF%B8%8F-real-time-behavior) for rationale.

---

## 📋 API Reference

| Endpoint | Method | Params | Description |
|---|---|---|---|
| `/health` | `GET` | None | API and database connectivity health check |
| `/api/v1/stats` | `GET` | None | Pipelines statistics (total ingested jobs, dead letters, database sizes) |
| `/api/v1/jobs` | `GET` | `page`, `limit`, `source` | Paginated raw job posting records from Bronze |
| `/api/v1/trends/countries`| `GET` | `limit`, `month`, `country` | Monthly aggregates filtered by country and month |
| `/api/v1/trends/skills` | `GET` | `limit`, `month`, `skill` | Monthly skill demand aggregates (explodes tags array) |
| `/api/v1/trends/roles` | `GET` | `limit`, `month`, `role` | Monthly demand for normalized role types |
| `/api/v1/trends/time` | `GET` | `limit`, `month` | Monthly total posting volume trends |

---

## 🔧 Environment Variables Reference

A `.env` file controls system configuration:

| Variable | Default Value | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///careerlens_local.db` | SQLAlchemy connection string (SQLite locally, PostgreSQL in Docker) |
| `REMOTIVE_API_URL` | `https://remotive.com/api/remote-jobs` | Source API URL endpoint |
| `FALLBACK_DATASET_PATH`| `data/fallback/kaggle_fallback.csv` | Relative or absolute path to local CSV fallback seed |
| `LOG_LEVEL` | `INFO` | Logger verbosity level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `PIPELINE_INTERVAL_MINUTES` | `5` | How often the scheduler runs the pipeline (minutes). See [Real-Time Behavior](#%EF%B8%8F-real-time-behavior). |

---

## 🧪 Testing & Code Quality

We maintain high code quality with automated unit, integration, and E2E tests:

```bash
# Run all tests
python -m pytest tests/ -v

# Run tests and output code coverage report
python -m pytest --cov=src --cov-report=term-missing
```

We follow PEP 8 formatting and clean coding guidelines. Lint and format code before contributing:
```bash
# Code style alignment (Black)
python -m black .

# Linter analysis and import sorting (Ruff)
python -m ruff check --fix .
```

---

## 🤝 Contributing

Contributions are welcome! Please read our [Contributing Guidelines](docs/CONTRIBUTING.md) for instructions on setting up your branch, running validation, and creating pull requests.
