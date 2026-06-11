from __future__ import annotations

import pytest
from src.ingestion.db import _engines, _sessionmakers


@pytest.fixture
def sqlite_db_url() -> str:
    return "sqlite://"


@pytest.fixture(autouse=True)
def reset_engine_cache() -> None:
    yield
    for engine in _engines.values():
        engine.dispose()
    _engines.clear()
    _sessionmakers.clear()
