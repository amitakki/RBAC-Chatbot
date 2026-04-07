"""Unit tests for Settings / config loading."""
from typing import Annotated

import pytest
from pydantic import ValidationError, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class _MinimalSettings(BaseSettings):
    """Isolated settings class so tests never read the real .env file."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    groq_api_key: str
    jwt_secret: str
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "finsolve_docs"
    redis_url: str = "redis://localhost:6379"
    environment: str = "local"
    prompt_version: str = "v1"


class _CorsSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    cors_allow_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    @field_validator("cors_allow_origins", mode="before")
    @classmethod
    def parse_cors_allow_origins(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.split("#", 1)[0].strip()
            if not cleaned:
                return []
            return [origin.strip() for origin in cleaned.split(",") if origin.strip()]
        return value


def test_valid_settings(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    s = _MinimalSettings()
    assert s.groq_api_key == "test-groq-key"
    assert s.jwt_secret == "test-jwt-secret"
    assert s.qdrant_url == "http://localhost:6333"
    assert s.environment == "local"


def test_missing_groq_api_key_raises(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    with pytest.raises(ValidationError) as exc_info:
        _MinimalSettings()
    errors = exc_info.value.errors()
    fields = [e["loc"][0] for e in errors]
    assert "groq_api_key" in fields


def test_missing_jwt_secret_raises(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(ValidationError) as exc_info:
        _MinimalSettings()
    errors = exc_info.value.errors()
    fields = [e["loc"][0] for e in errors]
    assert "jwt_secret" in fields


def test_defaults_applied(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    s = _MinimalSettings()
    assert s.qdrant_url == "http://localhost:6333"
    assert s.qdrant_collection == "finsolve_docs"
    assert s.redis_url == "redis://localhost:6379"
    assert s.prompt_version == "v1"


def test_env_override(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("QDRANT_COLLECTION", "my_custom_collection")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    s = _MinimalSettings()
    assert s.qdrant_collection == "my_custom_collection"
    assert s.environment == "staging"


def test_cors_allow_origins_parses_csv_env(monkeypatch):
    monkeypatch.setenv(
        "CORS_ALLOW_ORIGINS",
        "http://localhost:3000, https://example.com # frontend origins",
    )
    s = _CorsSettings()
    assert s.cors_allow_origins == ["http://localhost:3000", "https://example.com"]
