import types
from unittest.mock import MagicMock, patch

from app.rag.llm_factory import build_chat_model


def test_build_chat_model_returns_groq_client():
    mock_chat_groq = MagicMock()
    fake_module = types.SimpleNamespace(ChatGroq=mock_chat_groq)
    with (
        patch("app.rag.llm_factory.settings.llm_provider", "groq"),
        patch("app.rag.llm_factory.settings.groq_model", "llama-3.3-70b-versatile"),
        patch("app.rag.llm_factory.settings.groq_temperature", 0.1),
        patch("app.rag.llm_factory.settings.groq_timeout_seconds", 12),
        patch("app.rag.llm_factory.settings.groq_api_key", "test-key"),
        patch.dict("sys.modules", {"langchain_groq": fake_module}),
    ):
        client = build_chat_model()

    mock_chat_groq.assert_called_once_with(
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        request_timeout=12,
        api_key="test-key",
    )
    assert client is mock_chat_groq.return_value


def test_build_chat_model_returns_ollama_client():
    mock_chat_ollama = MagicMock()
    fake_module = types.SimpleNamespace(ChatOllama=mock_chat_ollama)
    with (
        patch("app.rag.llm_factory.settings.llm_provider", "ollama"),
        patch("app.rag.llm_factory.settings.ollama_model", "llama3.2"),
        patch("app.rag.llm_factory.settings.ollama_base_url", "http://localhost:11434"),
        patch("app.rag.llm_factory.settings.ollama_temperature", 0.2),
        patch("app.rag.llm_factory.settings.ollama_timeout_seconds", 30),
        patch.dict("sys.modules", {"langchain_ollama": fake_module}),
    ):
        client = build_chat_model()

    mock_chat_ollama.assert_called_once_with(
        model="llama3.2",
        base_url="http://localhost:11434",
        temperature=0.2,
        client_kwargs={"timeout": 30},
    )
    assert client is mock_chat_ollama.return_value
