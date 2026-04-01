"""
Unit tests for app/observability/logging_config.py (RC-125).

Tests verify:
- JSON formatter is attached to the root logger after configure_logging()
- configure_logging() is idempotent (safe to call multiple times)
- Log records serialise to valid JSON
- configure_logging() survives a missing pythonjsonlogger package gracefully
"""
from __future__ import annotations

import json
import logging
import sys
from io import StringIO
from unittest.mock import patch


def _reset_logging_config() -> None:
    """Reset the _CONFIGURED flag so configure_logging() can run again in tests."""
    import app.observability.logging_config as lc
    lc._CONFIGURED = False
    # Also clear root handlers to start fresh
    logging.getLogger().handlers.clear()


class TestConfigureLogging:
    def setup_method(self) -> None:
        _reset_logging_config()

    def teardown_method(self) -> None:
        _reset_logging_config()

    def test_attaches_handler_to_root_logger(self) -> None:
        from app.observability.logging_config import configure_logging
        configure_logging()
        root = logging.getLogger()
        assert len(root.handlers) == 1

    def test_handler_has_json_formatter(self) -> None:
        from app.observability.logging_config import configure_logging
        configure_logging()
        from pythonjsonlogger.jsonlogger import JsonFormatter
        handler = logging.getLogger().handlers[0]
        assert isinstance(handler.formatter, JsonFormatter)

    def test_idempotent_second_call_does_not_add_handler(self) -> None:
        from app.observability.logging_config import configure_logging
        configure_logging()
        configure_logging()  # second call
        assert len(logging.getLogger().handlers) == 1

    def test_log_record_is_valid_json(self) -> None:
        from app.observability.logging_config import configure_logging

        buf = StringIO()
        configure_logging()
        # Replace the stdout handler's stream with our buffer
        handler = logging.getLogger().handlers[0]
        handler.stream = buf

        test_logger = logging.getLogger("test.json")
        test_logger.info("test_event", extra={"foo": "bar"})

        output = buf.getvalue().strip()
        assert output, "Expected log output, got nothing"
        record = json.loads(output)
        assert record["message"] == "test_event"
        assert record["foo"] == "bar"
        assert "timestamp" in record
        assert "level" in record

    def test_survives_missing_pythonjsonlogger(self) -> None:
        from app.observability.logging_config import configure_logging

        mods = {"pythonjsonlogger": None, "pythonjsonlogger.jsonlogger": None}
        with patch.dict(sys.modules, mods):
            # Should not raise, falls back to basicConfig
            configure_logging()

        assert logging.getLogger().handlers  # some handler is present
