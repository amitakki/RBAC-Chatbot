"""Unit tests for Settings / config loading."""
from typing import Annotated

import pytest
from pydantic import ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class _MinimalSettings(BaseSettings):
    """Isolated settings class so tests never read the real .env file."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    llm_provider: str = "groq"
    groq_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str | None = None
    jwt_secret: str
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "finsolve_docs"
    redis_url: str = "redis://localhost:6379"
    environment: str = "local"
    prompt_version: str = "v1"

    @field_validator("llm_provider", mode="before")
    @classmethod
    def normalize_llm_provider(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("groq_api_key", "ollama_model", mode="before")
    @classmethod
    def empty_strings_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.split("#", 1)[0].strip()
            return cleaned or None
        return value

    @field_validator("llm_provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        if value not in {"groq", "ollama"}:
            raise ValueError("llm_provider")
        return value

    @model_validator(mode="after")
    def validate_llm_settings(self) -> "_MinimalSettings":
        if self.llm_provider == "groq" and not self.groq_api_key:
            raise ValueError("groq_api_key")
        if self.llm_provider == "ollama" and not self.ollama_model:
            raise ValueError("ollama_model")
        return self


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
    assert "groq_api_key" in str(exc_info.value)


def test_ollama_provider_without_groq_api_key_passes(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    s = _MinimalSettings()
    assert s.llm_provider == "ollama"
    assert s.ollama_model == "llama3.2"


def test_missing_ollama_model_raises(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret")
    with pytest.raises(ValidationError) as exc_info:
        _MinimalSettings()
    assert "ollama_model" in str(exc_info.value)


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


class _DynamicThresholdSettings(BaseSettings):
    """Settings class for testing dynamic threshold config."""

    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    retrieval_dynamic_threshold_enabled: bool = False
    retrieval_min_chunks: int = 1
    retrieval_max_chunks: int = 10
    reranker_min_score: float | None = None

    @field_validator("reranker_min_score", mode="before")
    @classmethod
    def empty_strings_to_none(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.split("#", 1)[0].strip()
            return cleaned or None
        return value


def test_dynamic_threshold_defaults(monkeypatch):
    """RC-163: dynamic threshold settings have correct defaults."""
    s = _DynamicThresholdSettings()
    assert s.retrieval_dynamic_threshold_enabled is False
    assert s.retrieval_min_chunks == 1
    assert s.retrieval_max_chunks == 10
    assert s.reranker_min_score is None


def test_dynamic_threshold_env_override(monkeypatch):
    """RC-163: dynamic threshold settings can be overridden."""
    monkeypatch.setenv("RETRIEVAL_DYNAMIC_THRESHOLD_ENABLED", "true")
    monkeypatch.setenv("RETRIEVAL_MIN_CHUNKS", "2")
    monkeypatch.setenv("RETRIEVAL_MAX_CHUNKS", "15")
    monkeypatch.setenv("RERANKER_MIN_SCORE", "0.5")
    s = _DynamicThresholdSettings()
    assert s.retrieval_dynamic_threshold_enabled is True
    assert s.retrieval_min_chunks == 2
    assert s.retrieval_max_chunks == 15
    assert s.reranker_min_score == 0.5


def test_reranker_min_score_empty_string_to_none(monkeypatch):
    """RC-163: empty RERANKER_MIN_SCORE converts to None."""
    monkeypatch.setenv("RERANKER_MIN_SCORE", "")
    s = _DynamicThresholdSettings()
    assert s.reranker_min_score is None
