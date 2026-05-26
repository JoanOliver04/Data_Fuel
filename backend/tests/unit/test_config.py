"""Tests for app.core.config.Settings."""

import pytest

from app.core.config import Settings, get_settings


def test_defaults_when_no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("DEBUG", raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_name == "Data Fuel API"
    assert settings.app_version == "0.1.0"
    assert settings.debug is False
    assert settings.default_km_cost == 0.13
    assert settings.allowed_origins == ["http://localhost:5173"]
    assert "sqlite+aiosqlite" in settings.database_url


def test_allowed_origins_from_csv_string(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://a.test, http://b.test ,  ,http://c.test")
    settings = get_settings()
    assert settings.allowed_origins == ["http://a.test", "http://b.test", "http://c.test"]


def test_allowed_origins_passthrough_for_list() -> None:
    """When given a list directly (not via env), the validator returns it untouched."""
    settings = Settings(
        _env_file=None,
        allowed_origins=["http://x.test", "http://y.test"],
    )
    assert settings.allowed_origins == ["http://x.test", "http://y.test"]


def test_get_settings_is_cached() -> None:
    a = get_settings()
    b = get_settings()
    assert a is b


def test_negative_km_cost_rejected() -> None:
    with pytest.raises(ValueError):
        Settings(_env_file=None, default_km_cost=-1.0)


def test_blank_retrain_guards_parse_as_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty `RETRAIN_MAX_MAE=` / `RETRAIN_MIN_R2=` mean 'disabled', not a parse error.

    `.env.example` ships these blank; without coercion pydantic would crash on
    boot trying to read "" as a float.
    """
    monkeypatch.setenv("RETRAIN_MAX_MAE", "")
    monkeypatch.setenv("RETRAIN_MIN_R2", "  ")
    settings = get_settings()
    assert settings.retrain_max_mae is None
    assert settings.retrain_min_r2 is None


def test_retrain_guards_still_parse_numbers() -> None:
    settings = Settings(_env_file=None, retrain_max_mae=0.05, retrain_min_r2=0.8)
    assert settings.retrain_max_mae == 0.05
    assert settings.retrain_min_r2 == 0.8
