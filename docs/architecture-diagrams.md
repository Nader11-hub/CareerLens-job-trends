# CareerLens — Architecture & Diagrams

---

## 1. Full Pipeline Flow

```mermaid
flowchart TD
    subgraph Sources["🌐 External Data Sources"]
        A1["🔗 Remotive API\nremotive.com/api/remote-jobs\nLive JSON — no API key needed"]
        A2["📄 Kaggle CSV\ndata/fallback/kaggle_fallback.csv\nOffline fallback dataset"]
    end

    subgraph Ingestion["⚙️ Layer 1 — Ingestion  (src/ingestion/)"]
        B1["fetcher.py\nHTTP GET + 3 retries\n(tenacity exponential back-off)"]
        B2["models.py\nPydantic JobRecord\nstrict schema validation"]
        B3["pipeline.py\nOrchestrate: fetch → validate → upsert"]
        B4["backfill.py\nDead-letter retry + sanitise"]
    end

    subgraph Bronze["🥉 Bronze Layer — MySQL"]
        C1[("bronze_jobs\n29,391 rows\nRaw validated records")]
        C2[("bronze_jobs_dead_letter\nInvalid records\nRetry queue")]
    end

    subgraph Transformation["🔄 Layer 2 — Transformation  (src/transformation/)"]
        D1["Python Runner\nrunner.py\nInfer country · parse salary\nclassify seniority · date grain"]
        D2["dbt Models\nsilver_jobs.sql\ngold_*.sql  schema.yml\n(MySQL 8 JSON_TABLE)"]
    end

    subgraph Silver["🥈 Silver Layer — MySQL"]
        E1[("silver_jobs\n29,391 rows\nNormalised + enriched")]
    end

    subgraph Gold["🥇 Gold Layer — MySQL"]
        F1[("gold_country_trends\n359 rows")]
        F2[("gold_skill_trends\n491 rows")]
        F3[("gold_role_trends\n1,259 rows")]
        F4[("gold_time_trends\n7 rows")]
    end

    subgraph Serving["🚀 Layer 3 — Serving  (src/serving/)"]
        G1["FastAPI\nport 8000\n13 REST endpoints\nSwagger UI /docs"]
        G2["Streamlit Dashboard\nport 8501\nChoropleth · Treemap\nBar charts · KPIs · AI Advisor"]
    end

    subgraph Orchestration["📅 Layer 4 — Orchestration  (src/orchestration/)"]
        H1["runner.py\nSingle-run CLI\n--source all/remotive/kaggle"]
        H2["scheduler.py\nAPScheduler\nRecurring every 5 min"]
        H3["email_alerts.py\nSMTP daily digest\nper-skill filtering"]
    end

    A1 -->|"Live JSON"| B1
    A2 -->|"CSV rows"| B1
    B1 -->|"raw dicts"| B2
    B2 -->|"valid records"| B3
    B2 -->|"invalid records"| B3
    B3 -->|"upsert"| C1
    B3 -->|"insert"| C2
    C2 -->|"retry"| B4
    B4 -->|"promote"| C1

    C1 --> D1
    C1 --> D2
    D1 --> E1
    D2 --> E1

    E1 --> F1
    E1 --> F2
    E1 --> F3
    E1 --> F4

    F1 --> G1
    F2 --> G1
    F3 --> G1
    F4 --> G1
    G1 -->|"REST JSON"| G2

    H2 -->|"triggers every 5 min"| H1
    H1 --> B3
    H1 --> D1
    H1 --> B4
```

---

## 2. Database Entity-Relationship Diagram

```mermaid
erDiagram
    BRONZE_JOBS {
        bigint  id                  PK
        varchar source
        text    url
        text    title
        text    company_name
        json    tags
        varchar job_type
        datetime publication_date
        varchar candidate_required_location
        varchar salary
        text    description
        datetime ingested_at
    }

    BRONZE_JOBS_DEAD_LETTER {
        int     id              PK
        varchar source
        json    raw_data
        text    error_message
        boolean resolved
        int     retry_count
        datetime created_at
        datetime resolved_at
    }

    SILVER_JOBS {
        bigint  job_id          PK
        varchar source
        text    title
        text    company_name
        text    role
        varchar country
        json    tags
        datetime publication_date
        date    published_date
        date    published_month
        float   salary_min
        float   salary_max
        varchar salary_currency
        varchar seniority
    }

    GOLD_COUNTRY_TRENDS {
        int     id              PK
        varchar country
        date    published_month
        int     job_count
    }

    GOLD_SKILL_TRENDS {
        int     id              PK
        varchar skill
        date    published_month
        int     job_count
    }

    GOLD_ROLE_TRENDS {
        int     id              PK
        varchar role
        date    published_month
        int     job_count
    }

    GOLD_TIME_TRENDS {
        int     id              PK
        date    published_month
        int     job_count
    }

    EMAIL_SUBSCRIPTIONS {
        int     id              PK
        varchar email
        varchar name
        json    skills
        boolean active
        datetime created_at
    }

    BOOKMARKED_JOBS {
        int     id              PK
        bigint  job_id
        text    notes
        datetime bookmarked_at
    }

    BRONZE_JOBS ||--o{ SILVER_JOBS        : "transformed into"
    SILVER_JOBS ||--o{ GOLD_COUNTRY_TRENDS : "grouped by country+month"
    SILVER_JOBS ||--o{ GOLD_SKILL_TRENDS   : "tag-exploded by skill+month"
    SILVER_JOBS ||--o{ GOLD_ROLE_TRENDS    : "grouped by role+month"
    SILVER_JOBS ||--o{ GOLD_TIME_TRENDS    : "grouped by month"
```

---

## 3. Data Journey — Explained Simply

| Step | What Happens | Input | Output |
|---|---|---|---|
| **1. Fetch** | Call Remotive API over the internet | URL request | Raw JSON |
| **2. Validate** | Check every field with Pydantic | Raw JSON | Valid / Invalid records |
| **3. Store Bronze** | Save valid records to MySQL | Valid records | `bronze_jobs` table |
| **4. Dead-letter** | Save invalid records separately | Invalid records | `bronze_jobs_dead_letter` |
| **5. Backfill** | Try to fix & retry invalid records | Dead-letters | Promoted to `bronze_jobs` |
| **6. Enrich** | Infer country, parse salary, classify seniority | `bronze_jobs` | `silver_jobs` |
| **7. Aggregate** | Count jobs by country / skill / role / month | `silver_jobs` | 4 Gold tables |
| **8. Serve API** | FastAPI reads gold tables → returns JSON | Gold tables | REST responses |
| **9. Visualise** | Streamlit calls API → renders charts | REST JSON | Dashboard |

---

## 4. Technology Stack at a Glance

| Layer | Technology | What It Does |
|---|---|---|
| **Data Collection** | `requests` + `tenacity` | HTTP calls with automatic retry |
| **Validation** | `Pydantic v2` | Type-safe schema enforcement |
| **Database ORM** | `SQLAlchemy 2.0` | Python ↔ MySQL mapping |
| **Database** | `MySQL 8.0` | Stores all 9 tables, 60,899 rows |
| **Transformation** | `Python` + `dbt-mysql` | Clean, aggregate, enrich data |
| **REST API** | `FastAPI` + `uvicorn` | 13 endpoints, auto Swagger docs |
| **Dashboard** | `Streamlit` + `Plotly` | Interactive charts & maps |
| **Scheduling** | `APScheduler` | Runs pipeline every 5 minutes |
| **Email Alerts** | `smtplib` (SMTP) | Daily job digest emails |
| **AI Features** | `Google Gemini 1.5` | Resume analysis & job matching |
| **Containerisation** | `Docker Compose` | One-command full stack deploy |
| **CI/CD** | `GitHub Actions` | Auto test on every code push |
| **Testing** | `pytest` + `pytest-cov` | Unit & integration tests |
| **Code Quality** | `black` + `ruff` | Auto formatting & linting |
| **Config** | `pydantic-settings` + `.env` | Secure environment config |

---

## 5. API Endpoints Map

```
http://localhost:8000/
│
├── /health                          ← Is the server alive?
├── /docs                            ← Interactive Swagger UI
│
├── /api/v1/
│   ├── stats                        ← KPIs: total jobs, countries, skills
│   │
│   ├── trends/
│   │   ├── countries?limit&month    ← Gold: jobs by country
│   │   ├── skills?limit&month       ← Gold: jobs by skill/technology
│   │   ├── roles?limit&month        ← Gold: jobs by role title
│   │   └── time?limit               ← Gold: monthly job count
│   │
│   ├── jobs?page&source&seniority   ← Bronze: paginated job browser
│   │
│   ├── salary/
│   │   ├── by-role?currency         ← Avg salary per role
│   │   ├── by-country?currency      ← Avg salary per country
│   │   └── currencies               ← Available currencies
│   │
│   ├── bookmarks/                   ← GET / POST / DELETE
│   ├── subscriptions/               ← POST email alert subscription
│   ├── unsubscribe/                 ← DELETE subscription
│   └── ai/recommend                 ← POST resume → AI job matches
```

---

## 6. Live System Stats (MySQL — right now)

| Metric | Value |
|---|---|
| 🗄️ Database | MySQL 8.0 — `careerlens` |
| 📋 Bronze jobs | **29,391** job postings |
| ✨ Silver jobs | **29,391** enriched records |
| 🌍 Countries tracked | **359** country/region combinations |
| 🔧 Skills tracked | **491** unique skills |
| 👔 Role types | **1,259** unique role titles |
| 📅 Time coverage | **7 months** of data |
| 📦 Total rows | **60,899** across all tables |
| ⚡ Migration speed | 60,899 rows in **8.2 seconds** |
| 🚀 API | Running on `http://localhost:8000` |
| 📊 Dashboard | Running on `http://localhost:8501` |

---

## 7. How to Run Everything

```bash
# 1. Activate virtual environment
venv\Scripts\activate

# 2. Run the full pipeline once (fetch + transform + backfill)
python -m src.orchestration.runner --source all

# 3. Start the API server
python -m uvicorn src.serving.api.main:app --port 8000

# 4. Start the dashboard (new terminal)
python -m streamlit run src/serving/dashboard/app.py

# --- OR run everything at once ---
python run.py

# --- OR deploy with Docker ---
docker compose up --build
```
