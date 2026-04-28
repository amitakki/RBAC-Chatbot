"""Shared pytest fixtures for backend tests."""
import os
import pytest


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    """Ensure no real .env bleeds into unit tests."""
    for key in (
        "LLM_PROVIDER",
        "GROQ_API_KEY",
        "OLLAMA_BASE_URL",
        "OLLAMA_MODEL",
        "JWT_SECRET",
        "LANGSMITH_API_KEY",
        "QDRANT_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
