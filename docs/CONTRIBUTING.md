# Contributing to CareerLens

Thank you for your interest in contributing to CareerLens! This document provides guidelines for setting up your development environment, writing code, running tests, and preparing contributions.

---

## 1. Development Setup

### Prerequisites
- Python 3.11 or later
- SQLite (default for development/testing)
- PostgreSQL 16 (for production simulations/dbt transformations)
- Docker & Docker Compose (optional, for containerized execution)

### Initial Repository Setup
1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/job-trends-pipeline.git
   cd job-trends-pipeline
   ```

2. **Set up a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Copy the example environment configuration and adjust it:
   ```bash
   cp .env.example .env
   ```
   For local development with SQLite, the defaults in `.env.example` are preconfigured.

---

## 2. Code Quality & Formatting

To maintain a consistent and clean codebase, we enforce strict formatting and linting rules using **Black** and **Ruff**.

### Code Style Guidelines
- **Type Hints**: All function signatures, including return types, should have explicit type hints.
- **Docstrings**: Document all modules, classes, and public functions using the Google Docstring style.
- **Imports**: Group imports into standard library, third-party libraries, and local modules, sorted alphabetically (handled automatically by Ruff).

### Formatting and Linting Commands
Before submitting any changes, format your code and run static analysis:

*   **Code formatting (Black):**
    ```bash
    python -m black .
    ```

*   **Linting and Auto-fixes (Ruff):**
    ```bash
    python -m ruff check --fix .
    ```

*   **Linter check (without modifications):**
    ```bash
    python -m ruff check .
    ```

---

## 3. Running the Pipeline & API

You can run individual parts of the system or spin up the full orchestration workflow.

### Single Pipeline Run (Ingestion & Transformation)
To execute the ingestion and transformation steps once:
```bash
# Ingest live Remotive API data and process with the Python runner
python -m src.orchestration.runner --source remotive

# Fall back to the Kaggle CSV seed data for offline development
python -m src.orchestration.runner --source kaggle
```

### Recurring Pipeline (Scheduler)
To run the scheduler in the foreground, triggering a pipeline execution every 30 minutes:
```bash
python -m src.orchestration.runner --schedule-interval 30
```

### Standalone Dead-Letter Backfill
To run a dry-run analysis of the current dead-letter records:
```bash
python -m src.ingestion.backfill_cli --dry-run
```
To attempt recovery and promotion of fixable records:
```bash
python -m src.ingestion.backfill_cli --limit 100
```

### API & Dashboard Servers
*   **Start the FastAPI REST API:**
    ```bash
    uvicorn src.serving.api.main:app --reload
    ```
    Access the OpenAPI documentation at `http://localhost:8000/docs`.

*   **Start the Streamlit Dashboard:**
    ```bash
    streamlit run src/serving/dashboard/app.py
    ```

---

## 4. Testing

We use **pytest** for unit, integration, and end-to-end tests.

### Running Tests
To run all tests in the suite:
```bash
python -m pytest tests/ -v
```

### Code Coverage
Generate an XML code coverage report and view coverage statistics:
```bash
python -m pytest --cov=src --cov-report=term-missing
```

---

## 5. dbt (Data Build Tool) Transformations

For production scenarios, we use dbt to compile and execute SQL-based medallion transformations on PostgreSQL.

### Running dbt Models
Ensure your PostgreSQL database is running, then execute:
```bash
dbt run --project-dir src/transformation --profiles-dir src/transformation
```

### Running dbt Schema Tests
```bash
dbt test --project-dir src/transformation --profiles-dir src/transformation
```

### Compiling Documentation
Generate and serve local dbt model documentation:
```bash
dbt docs generate --project-dir src/transformation --profiles-dir src/transformation
dbt docs serve --project-dir src/transformation --profiles-dir src/transformation
```

---

## 6. Dockerized Environment

Verify container builds and orchestrate the stack locally:
```bash
# Build and run the entire ecosystem (postgres, api, dashboard, scheduler)
docker compose up --build

# Run only the one-shot pipeline container (uses the postgres container)
docker compose run pipeline
```

---

## 7. Submission Checklist

Before submitting a Pull Request, verify that:
1. [ ] The code runs successfully locally.
2. [ ] All unit and integration tests pass (`pytest`).
3. [ ] Code passes formatting checks (`black --check .`).
4. [ ] Code passes linting checks (`ruff check .`).
5. [ ] Python type annotations and Google-style docstrings are complete.
6. [ ] The data model documentation or SRS is updated if schemas or requirements have changed.
