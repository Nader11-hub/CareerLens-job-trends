"""
migrate_sqlite_to_mysql.py
──────────────────────────
Copies every table from the local SQLite database (careerlens_local.db)
into the MySQL database defined in .env, in batches.

Usage
-----
    # Make sure MySQL is running first, then:
    venv\\Scripts\\python.exe migrate_sqlite_to_mysql.py

    # Override either URL on the command line:
    venv\\Scripts\\python.exe migrate_sqlite_to_mysql.py \
        --sqlite sqlite:///careerlens_local.db \
        --mysql  mysql+pymysql://root:nader@127.0.0.1:3306/careerlens?charset=utf8mb4
"""

from __future__ import annotations

import argparse
import sys
import time
from typing import Any

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

# ── defaults ──────────────────────────────────────────────────────────────────
SQLITE_URL = "sqlite:///careerlens_local.db"
MYSQL_URL  = "mysql+pymysql://root:nader@127.0.0.1:3306/careerlens?charset=utf8mb4"

# Tables in dependency order (parents before children)
TABLES = [
    "bronze_jobs",
    "bronze_jobs_dead_letter",
    "silver_jobs",
    "gold_country_trends",
    "gold_skill_trends",
    "gold_role_trends",
    "gold_time_trends",
    "email_subscriptions",
    "bookmarked_jobs",
]

BATCH_SIZE = 500


# ─────────────────────────────────────────────────────────────────────────────
def build_engine(url: str, is_mysql: bool = False) -> Engine:
    if is_mysql:
        return create_engine(url, pool_pre_ping=True, pool_recycle=3600, future=True)
    return create_engine(url, future=True)


def ensure_mysql_db(mysql_url: str) -> None:
    """Create the target database if it does not exist yet."""
    from urllib.parse import urlparse, urlunparse
    parsed = urlparse(mysql_url.split("?")[0])
    db_name = parsed.path.lstrip("/")
    root_url = urlunparse(parsed._replace(path="/")) + "?charset=utf8mb4"
    engine = create_engine(root_url, future=True)
    with engine.connect() as conn:
        conn.execute(text(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        ))
        conn.commit()
    engine.dispose()
    print(f"  v  Database `{db_name}` ready.")


def _progress(table: str, done: int, total: int) -> None:
    pct = done / total * 100 if total else 100
    bar = "#" * int(pct // 5) + "." * (20 - int(pct // 5))
    print(f"\r  ~  {table:<30} [{bar}] {pct:5.1f}%  {done:,}/{total:,}", end="", flush=True)


def migrate_table(src: Engine, dst: Engine, table_name: str) -> int:
    """Copy all rows from *table_name* in src to dst. Returns row count."""

    src_insp = inspect(src)
    if table_name not in src_insp.get_table_names():
        print(f"  !  Table '{table_name}' not found in source -- skipping.")
        return 0

    with src.connect() as src_conn, dst.connect() as dst_conn:
        total: int = src_conn.execute(
            text(f"SELECT COUNT(*) FROM `{table_name}`")
        ).scalar() or 0

        if total == 0:
            print(f"  -  {table_name:<35} empty -- skipping.")
            return 0

        # Truncate destination to avoid duplicate-key errors on re-run
        dst_conn.execute(text("SET FOREIGN_KEY_CHECKS=0"))
        dst_conn.execute(text(f"TRUNCATE TABLE `{table_name}`"))
        dst_conn.execute(text("SET FOREIGN_KEY_CHECKS=1"))
        dst_conn.commit()

        result = src_conn.execute(text(f"SELECT * FROM `{table_name}`"))
        cols = list(result.keys())

        inserted = 0
        batch: list[dict[str, Any]] = []

        for row in result:
            batch.append(dict(zip(cols, row)))
            if len(batch) >= BATCH_SIZE:
                dst_conn.execute(
                    text(
                        f"INSERT INTO `{table_name}` "
                        f"({', '.join(f'`{c}`' for c in cols)}) "
                        f"VALUES ({', '.join(f':{c}' for c in cols)})"
                    ),
                    batch,
                )
                dst_conn.commit()
                inserted += len(batch)
                batch = []
                _progress(table_name, inserted, total)

        if batch:
            dst_conn.execute(
                text(
                    f"INSERT INTO `{table_name}` "
                    f"({', '.join(f'`{c}`' for c in cols)}) "
                    f"VALUES ({', '.join(f':{c}' for c in cols)})"
                ),
                batch,
            )
            dst_conn.commit()
            inserted += len(batch)

    print(f"\r  OK {table_name:<35} {inserted:>7,} rows migrated.")
    return inserted


# ─────────────────────────────────────────────────────────────────────────────
def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Migrate SQLite to MySQL")
    parser.add_argument("--sqlite", default=SQLITE_URL, help="SQLite source URL")
    parser.add_argument("--mysql",  default=MYSQL_URL,  help="MySQL target URL")
    args = parser.parse_args(argv)

    print("\n  CareerLens  SQLite -> MySQL Migration")
    print("=" * 55)
    print(f"  Source : {args.sqlite}")
    print(f"  Target : {args.mysql}")
    print("=" * 55)

    # 1. Ensure MySQL DB exists
    print("\n[1/3] Ensuring target database exists...")
    try:
        ensure_mysql_db(args.mysql)
    except Exception as exc:
        print(f"\n  ERROR: Cannot reach MySQL: {exc}")
        print(
            "\n  Make sure the MySQL80 service is running.\n"
            "  Open PowerShell AS ADMINISTRATOR and run:\n"
            "      net start MySQL80\n"
        )
        sys.exit(1)

    # 2. Create schema in MySQL
    print("\n[2/3] Creating schema in MySQL...")
    from src.ingestion.db import init_db
    init_db(db_url=args.mysql)
    print("  v  Schema ready.")

    # 3. Migrate data
    print("\n[3/3] Copying data...\n")
    src_engine = build_engine(args.sqlite, is_mysql=False)
    dst_engine = build_engine(args.mysql,  is_mysql=True)

    t0 = time.time()
    grand_total = 0
    for table in TABLES:
        grand_total += migrate_table(src_engine, dst_engine, table)

    elapsed = time.time() - t0
    print(f"\n{'=' * 55}")
    print(f"  DONE!  {grand_total:,} rows migrated in {elapsed:.1f}s")
    print(f"{'=' * 55}\n")

    src_engine.dispose()
    dst_engine.dispose()


if __name__ == "__main__":
    main()
