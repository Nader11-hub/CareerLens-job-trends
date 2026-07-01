# 🎓 CareerLens — Project Overview
### Data Engineering Pipeline for Global Job Market Trends

**Student Presentation Document** | June 2026

---

## 🎯 What Is This Project?

**CareerLens** is a complete, production-grade **Data Engineering Pipeline** that automatically:

1. **Collects** live remote job postings from the internet
2. **Validates & Stores** every record in a structured database
3. **Transforms** raw data into clean, analytics-ready tables
4. **Serves** the data through a REST API
5. **Visualises** job market trends on an interactive dashboard

> The pipeline currently holds **29,391 real job postings** across **60,899 database rows** — migrated and running live in **MySQL**.

---

## 🛠️ Tools & Technologies Used

| Category | Tool | Version | Purpose |
|---|---|---|---|
| **Language** | Python | 3.14 | All application logic |
| **Web Framework** | FastAPI | 0.111+ | REST API backend |
| **Dashboard** | Streamlit | 1.36+ | Interactive web dashboard |
| **Charts** | Plotly | 5.22+ | Choropleth maps, treemaps, bar charts |
| **ORM / Database** | SQLAlchemy | 2.0+ | Database abstraction layer |
| **Database (prod)** | MySQL 8.0 | 8.0 | Primary production database |
| **Database (dev)** | SQLite | built-in | Local development & testing |
| **Data Validation** | Pydantic | 2.7+ | Schema validation of job records |
| **Config Management** | pydantic-settings | 2.3+ | Environment variable loading |
| **Transformation** | dbt-core | 1.8+ | SQL-first transformation models |
| **Scheduling** | APScheduler | 3.10+ | Recurring pipeline execution |
| **HTTP Client** | requests + tenacity | — | API fetching with retry logic |
| **Containerisation** | Docker + Compose | 29.1 | Full stack deployment |
| **CI/CD** | GitHub Actions | — | Automated testing & linting |
| **Code Quality** | black + ruff | — | Formatting & linting |
| **Testing** | pytest + pytest-cov | 8.2+ | Unit & integration tests |
| **Exports** | openpyxl | 3.1+ | Excel export capability |
| **AI Features** | Google Gemini API | 1.5-flash | AI-powered job recommendations |

---

## 🏗️ Architecture: The Medallion Pattern

The project follows the industry-standard **Medallion Architecture** — data passes through three quality layers:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      CAREERLENS PIPELINE                            │
│                                                                     │
│  🌐 SOURCES          🥉 BRONZE         🥈 SILVER       🥇 GOLD      │
│  ─────────────       ────────────      ──────────      ──────────── │
│  Remotive API   ──►  bronze_jobs  ──►  silver_jobs ──► country_     │
│  (live JSON)         (raw valid.)      (enriched)      trends       │
│                                                    ──► skill_       │
│  Kaggle CSV    ──►  dead_letter                        trends       │
│  (fallback)         (invalid rec.)                 ──► role_        │
│                           │                            trends       │
│                           └─► backfill ──► bronze  ──► time_        │
│                                                        trends       │
└─────────────────────────────────────────────────────────────────────┘
         │                                        │
         ▼                                        ▼
   ⚙️ FastAPI (port 8000)              📊 Streamlit Dashboard (port 8501)
   REST API endpoints                  Interactive charts & KPIs
```

---

## 📂 Project Structure

```
job-trends-pipeline/
│
├── src/
│   ├── ingestion/          ← Layer 1: Data collection & storage
│   │   ├── fetcher.py      ← HTTP requests to Remotive API + Kaggle CSV
│   │   ├── models.py       ← Pydantic JobRecord validation schema
│   │   ├── pipeline.py     ← Orchestrates fetch → validate → persist
│   │   ├── db.py           ← SQLAlchemy models + all 9 database tables
│   │   └── backfill.py     ← Retries failed (dead-letter) records
│   │
│   ├── transformation/     ← Layer 2: Data cleaning & aggregation
│   │   ├── runner.py       ← Python transformation engine
│   │   ├── models/
│   │   │   ├── silver/     ← silver_jobs.sql  (dbt model)
│   │   │   └── gold/       ← gold_skill_trends.sql, etc. (dbt models)
│   │   ├── dbt_project.yml ← dbt configuration
│   │   └── profiles.yml    ← dbt database profiles
│   │
│   ├── serving/            ← Layer 3: Data delivery
│   │   ├── api/
│   │   │   ├── main.py     ← FastAPI app + all routes
│   │   │   ├── service.py  ← Business logic queries
│   │   │   └── schemas.py  ← Pydantic response models
│   │   └── dashboard/
│   │       └── app.py      ← Streamlit 1,500-line dashboard
│   │
│   ├── orchestration/      ← Layer 4: Pipeline coordination
│   │   ├── runner.py       ← Single-run CLI entry point
│   │   ├── scheduler.py    ← APScheduler recurring runs
│   │   └── email_alerts.py ← Daily job alert digest emails
│   │
│   └── config.py           ← Centralised settings (pydantic-settings)
│
├── tests/                  ← Automated test suite (pytest)
├── docker-compose.yml      ← Full stack: mysql + api + dashboard
├── .env                    ← Environment configuration
└── migrate_sqlite_to_mysql.py ← Data migration tool (SQLite → MySQL)
```

---

## 🔄 Pipeline Flow — Step by Step

### Step 1: Ingestion (`src/ingestion/`)

```
Remotive API ──► fetcher.py  ──► Pydantic validation ──► bronze_jobs (MySQL)
                 (HTTP GET,       (models.py)              29,391 rows ✅
                  3 retries,
                  exponential
                  back-off)
                               └─► Invalid records ──► bronze_jobs_dead_letter
                                   (backfill.py           (retry queue)
                                    retries them)
```

**What happens:**
- `fetcher.py` calls the Remotive API (no API key needed) and gets JSON job listings
- Every record is validated by `Pydantic JobRecord`: URL must be valid, title/company must be non-blank, dates are normalized to UTC
- Valid jobs are **upserted** into `bronze_jobs` (idempotent — no duplicates)
- Invalid jobs go to `bronze_jobs_dead_letter` with the error message
- `backfill.py` automatically retries dead-letter records on each run

---

### Step 2: Transformation (`src/transformation/`)

```
bronze_jobs (29,391 rows)
    │
    ├─► _infer_country()      → "USA, New York" → "New York"
    ├─► _classify_seniority() → title contains "Senior" → "Senior"
    ├─► _parse_salary()       → "$80k–120k/yr" → min=80000 max=120000 USD
    ├─► _first_of_month()     → 2025-06-15 → 2025-06-01 (aggregation grain)
    │
    ▼
silver_jobs (29,391 enriched rows)
    │
    ├─► GROUP BY country, month      → gold_country_trends  (359 rows)
    ├─► UNNEST tags, GROUP BY skill  → gold_skill_trends    (491 rows)
    ├─► GROUP BY role, month         → gold_role_trends   (1,259 rows)
    └─► GROUP BY month               → gold_time_trends       (7 rows)
```

**Two transformation engines:**
- **Python Runner** — for MySQL/SQLite (what we use now)
- **dbt Models** — SQL-first alternative with `JSON_TABLE()` for MySQL 8.0

---

### Step 3: Serving (`src/serving/`)

#### REST API (FastAPI — port 8000)

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Liveness check → `{"status": "ok"}` |
| GET | `/api/v1/stats` | Total jobs, countries, skills, date range |
| GET | `/api/v1/trends/countries` | Jobs by country (filter by month, country) |
| GET | `/api/v1/trends/skills` | Jobs by skill (filter by month, skill) |
| GET | `/api/v1/trends/roles` | Jobs by role (filter by month, role) |
| GET | `/api/v1/trends/time` | Monthly job count time-series |
| GET | `/api/v1/jobs` | Paginated bronze job browser |
| GET | `/api/v1/salary/by-role` | Average salary per role |
| GET | `/api/v1/salary/by-country` | Average salary per country |
| GET | `/api/v1/bookmarks` | User-saved job bookmarks |
| POST | `/api/v1/bookmarks` | Save a job bookmark |
| POST | `/api/v1/subscriptions` | Subscribe to email alerts |
| POST | `/api/v1/ai/recommend` | AI job recommendations (Gemini) |
| GET | `/docs` | Interactive Swagger UI |

#### Dashboard (Streamlit — port 8501)

| Section | Visualisation | Data Source |
|---|---|---|
| KPI Bar | Total jobs, countries, skills, date range | `/api/v1/stats` |
| World Map | Choropleth map — jobs per country | `/api/v1/trends/countries` |
| Skills | Treemap of top 40 skills | `/api/v1/trends/skills` |
| Roles | Horizontal bar chart of top roles | `/api/v1/trends/roles` |
| Time Series | Area chart of monthly job counts | `/api/v1/trends/time` |
| Salary | Bar charts by role and country | `/api/v1/salary/*` |
| Job Browser | Searchable paginated job table | `/api/v1/jobs` |
| Bookmarks | Save & annotate favourite jobs | `/api/v1/bookmarks` |
| AI Advisor | Resume analysis + job matching | `/api/v1/ai/recommend` |

---

### Step 4: Orchestration (`src/orchestration/`)

```
python -m src.orchestration.runner --source all
    │
    ├─► run_ingestion()        ← Step 1: Fetch + validate + store
    ├─► run_transformations()  ← Step 2: Bronze → Silver → Gold
    └─► run_dead_letter_backfill() ← Step 3: Retry failed records
```

- **Single run:** `python -m src.orchestration.runner --source all`
- **Scheduled:** `--schedule-interval 5` → runs every 5 minutes via APScheduler
- **Sources:** `remotive` | `kaggle` | `all`

---

## 🗄️ Database Tables in MySQL (`careerlens`)

| Table | Layer | Rows | Purpose |
|---|---|---|---|
| `bronze_jobs` | 🥉 Bronze | 29,391 | Raw validated job postings |
| `bronze_jobs_dead_letter` | 🥉 Bronze | 0 | Failed validation records (retry queue) |
| `silver_jobs` | 🥈 Silver | 29,391 | Enriched & normalised jobs |
| `gold_country_trends` | 🥇 Gold | 359 | Jobs aggregated by country + month |
| `gold_skill_trends` | 🥇 Gold | 491 | Jobs aggregated by skill + month |
| `gold_role_trends` | 🥇 Gold | 1,259 | Jobs aggregated by role + month |
| `gold_time_trends` | 🥇 Gold | 7 | Jobs aggregated by month only |
| `email_subscriptions` | 🔔 Feature | 0 | Job alert email subscribers |
| `bookmarked_jobs` | 🔖 Feature | 1 | User-saved job bookmarks |
| **Total** | | **60,899** | |

---

## 🐳 Docker Deployment

The full stack runs with a single command:

```bash
docker compose up --build
```

This starts **5 containers**:

| Container | Port | Role |
|---|---|---|
| `mysql` | 3306 | MySQL 8.0 database |
| `pipeline` | — | One-shot ingestion + transform run |
| `scheduler` | — | Recurring pipeline (every 5 min) |
| `api` | 8000 | FastAPI REST server |
| `dashboard` | 8501 | Streamlit dashboard |

---

## ✅ Code Quality & Testing

| Check | Tool | Command |
|---|---|---|
| Unit Tests | pytest | `pytest tests/` |
| Coverage | pytest-cov | `pytest --cov=src` |
| Formatting | black | `black --check .` |
| Linting | ruff | `ruff check .` |
| CI/CD | GitHub Actions | Runs on every push |

**Test files cover:**
- `test_ingestion.py` — Pydantic validation, fetcher, pipeline
- `test_bookmarks.py` — Bookmark CRUD operations
- `test_enrichment.py` — Salary parsing, seniority classification, country inference

---

## 🌐 Running the Project Locally

```
MySQL:     running as Windows service (MySQL80)
FastAPI:   http://localhost:8000/docs  ← API + Swagger UI
Streamlit: http://localhost:8501       ← Dashboard
```

**Start command:**
```bash
venv\Scripts\python.exe run.py
```

---

## 📊 Key Metrics

| Metric | Value |
|---|---|
| Total job postings collected | **29,391** |
| Total database rows | **60,899** |
| Data sources | Remotive API + Kaggle CSV |
| Countries detected | **359 unique country/region combinations** |
| Skills tracked | **491 unique skills** |
| Role types | **1,259 unique role titles** |
| Time range | Monthly aggregations across **7 months** |
| Migration speed | 60,899 rows migrated in **8.2 seconds** |
