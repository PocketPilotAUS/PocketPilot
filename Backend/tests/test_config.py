import pytest

from app.core.config import (
    ConfigurationError,
    DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES,
    get_access_token_expire_minutes,
    get_jwt_secret_key
)

VALID_SECRET = "a" * 32


def test_missing_secret_raises_error(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(ConfigurationError, match="JWT_SECRET_KEY is not set"):
        get_jwt_secret_key()


def test_blank_secret_raises_error(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "   ")

    with pytest.raises(ConfigurationError, match="JWT_SECRET_KEY is not set"):
        get_jwt_secret_key()


def test_short_secret_raises_error(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", "a" * 31)

    with pytest.raises(ConfigurationError, match="at least 32"):
        get_jwt_secret_key()


def test_valid_secret_is_returned(monkeypatch):
    monkeypatch.setenv("JWT_SECRET_KEY", VALID_SECRET)

    assert get_jwt_secret_key() == VALID_SECRET


def test_expire_minutes_default(monkeypatch):
    monkeypatch.delenv("ACCESS_TOKEN_EXPIRE_MINUTES", raising=False)

    assert get_access_token_expire_minutes() == DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES


def test_expire_minutes_custom_value(monkeypatch):
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")

    assert get_access_token_expire_minutes() == 60


@pytest.mark.parametrize("value", ["abc", "0", "-5", "1441"])
def test_invalid_expire_minutes_raise_error(monkeypatch, value):
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", value)

    with pytest.raises(ConfigurationError):
        get_access_token_expire_minutes()


def test_api_starts_without_secret(monkeypatch):
    # Existing endpoints must keep working even when auth is not configured
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        assert client.get("/").status_code == 200
