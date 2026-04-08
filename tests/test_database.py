from __future__ import annotations

from cliptrans.adapters.persistence.database import get_engine


def test_get_engine_is_cached_per_database_url() -> None:
    memory_engine = get_engine("sqlite+aiosqlite://")
    file_engine = get_engine("sqlite+aiosqlite:////tmp/cliptrans-test.sqlite3")

    assert memory_engine is get_engine("sqlite+aiosqlite://")
    assert file_engine is get_engine("sqlite+aiosqlite:////tmp/cliptrans-test.sqlite3")
    assert memory_engine is not file_engine
