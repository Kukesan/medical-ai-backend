import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from types import SimpleNamespace

import pytest

from app.core.logging_config import configure_logging


@pytest.fixture(autouse=True)
def clear_root_logger() -> None:
    root_logger = __import__("logging").getLogger()

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()


def test_configure_logging_adds_daily_error_file_handler(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(
        "app.core.logging_config.settings",
        SimpleNamespace(log_path=tmp_path, error_log_retention_days=14),
    )

    configure_logging()

    root_logger = __import__("logging").getLogger()
    error_handlers = [
        handler
        for handler in root_logger.handlers
        if isinstance(handler, TimedRotatingFileHandler) and handler.level == __import__("logging").ERROR
    ]

    assert len(error_handlers) == 1
    expected_log_file = tmp_path / f"error-{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.getLogger("test.logging").error("daily error log test")

    assert error_handlers[0].baseFilename == str(expected_log_file)
    assert error_handlers[0].when == "MIDNIGHT"
    assert error_handlers[0].backupCount == 14
    assert expected_log_file.exists()
    assert "daily error log test" in expected_log_file.read_text(encoding="utf-8")