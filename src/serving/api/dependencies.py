from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from src.ingestion.db import get_session, init_db

# Initialize database schemas once at import time, not per-request.
init_db()


def get_db() -> Generator[Session, None, None]:
    session = get_session()
    try:
        yield session
    finally:
        session.close()
