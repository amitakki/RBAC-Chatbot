from __future__ import annotations

import importlib

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import settings


def build_chat_model() -> BaseChatModel:
    """Return the configured chat model for the active provider."""
    if settings.llm_provider == "ollama":
        chat_ollama = importlib.import_module("langchain_ollama").ChatOllama
        return chat_ollama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=settings.ollama_temperature,
            client_kwargs={"timeout": settings.ollama_timeout_seconds},
        )

    chat_groq = importlib.import_module("langchain_groq").ChatGroq
    return chat_groq(
        model=settings.groq_model,
        temperature=settings.groq_temperature,
        request_timeout=settings.groq_timeout_seconds,
        api_key=settings.groq_api_key,
    )
