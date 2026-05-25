"""DATABASE_URL normalization + dialect detection."""

import pytest

from app.core.config import Settings


def _settings(url: str) -> Settings:
    return Settings(database_url=url, _env_file=None)  # type: ignore[call-arg]


def test_bare_postgres_scheme_upgraded_to_asyncpg() -> None:
    s = _settings("postgres://u:p@h:5432/db")
    assert s.database_url == "postgresql+asyncpg://u:p@h:5432/db"
    assert s.is_postgres is True


def test_postgresql_scheme_upgraded_to_asyncpg() -> None:
    assert _settings("postgresql://u:p@h/db").database_url.startswith("postgresql+asyncpg://")


def test_sqlite_url_preserved() -> None:
    s = _settings("sqlite+aiosqlite:///./x.db")
    assert s.is_postgres is False
    assert s.database_url == "sqlite+aiosqlite:///./x.db"


def test_unsupported_scheme_rejected() -> None:
    with pytest.raises(ValueError, match="async drivers"):
        _settings("mysql://user@host/db")
