from __future__ import annotations

import importlib.util
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


_MODULE_PATH = Path(__file__).resolve().parents[3] / "evals" / "run_ragas.py"
_SPEC = importlib.util.spec_from_file_location("evals_run_ragas", _MODULE_PATH)
run_ragas = importlib.util.module_from_spec(_SPEC)
assert _SPEC is not None and _SPEC.loader is not None
_SPEC.loader.exec_module(run_ragas)


def test_build_langchain_llm_returns_groq_client(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("GROQ_TEMPERATURE", "0.1")
    monkeypatch.setenv("GROQ_TIMEOUT_SECONDS", "12")

    mock_chat_groq = MagicMock()
    fake_module = types.SimpleNamespace(ChatGroq=mock_chat_groq)

    with patch.object(run_ragas, "sys") as mock_sys, patch.dict("sys.modules", {"langchain_groq": fake_module}):
        client = run_ragas.build_langchain_llm()

    mock_sys.exit.assert_not_called()
    mock_chat_groq.assert_called_once_with(
        model="llama-3.3-70b-versatile",
        api_key="test-key",
        temperature=0.1,
        request_timeout=12,
    )
    assert client is mock_chat_groq.return_value


def test_build_langchain_llm_returns_ollama_client(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_TEMPERATURE", "0.2")
    monkeypatch.setenv("OLLAMA_TIMEOUT_SECONDS", "30")

    mock_chat_ollama = MagicMock()
    fake_module = types.SimpleNamespace(ChatOllama=mock_chat_ollama)

    with patch.object(run_ragas, "sys") as mock_sys, patch.dict("sys.modules", {"langchain_ollama": fake_module}):
        client = run_ragas.build_langchain_llm()

    mock_sys.exit.assert_not_called()
    mock_chat_ollama.assert_called_once_with(
        model="llama3.2",
        base_url="http://localhost:11434",
        temperature=0.2,
        client_kwargs={"timeout": 30},
    )
    assert client is mock_chat_ollama.return_value


def test_build_langchain_llm_requires_selected_provider_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        run_ragas.build_langchain_llm()

    assert "OLLAMA_MODEL" in str(exc_info.value)
