import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import sys
import time
from datetime import datetime

import structlog

from app.core.config import settings


class DateBasedErrorFileHandler(TimedRotatingFileHandler):
    def __init__(self, log_dir: Path, retention_days: int) -> None:
        self.log_dir = log_dir
        super().__init__(
            filename=self._current_log_path(),
            when="midnight",
            interval=1,
            backupCount=retention_days,
            encoding="utf-8",
        )

    def _current_log_path(self) -> str:
        return str(self.log_dir / f"error-{datetime.now().strftime('%Y-%m-%d')}.log")

    def getFilesToDelete(self) -> list[str]:
        log_files = sorted(self.log_dir.glob("error-*.log"))
        if len(log_files) <= self.backupCount:
            return []

        return [str(path) for path in log_files[: len(log_files) - self.backupCount]]

    def doRollover(self) -> None:
        if self.stream:
            self.stream.close()
            self.stream = None

        self.baseFilename = self._current_log_path()
        self.rolloverAt = self.computeRollover(int(time.time()))

        for old_file in self.getFilesToDelete():
            Path(old_file).unlink(missing_ok=True)

        if not self.delay:
            self.stream = self._open()


def _build_error_log_handler(log_dir: Path, retention_days: int) -> DateBasedErrorFileHandler:
    handler = DateBasedErrorFileHandler(
        log_dir=log_dir,
        retention_days=retention_days,
    )
    handler.setLevel(logging.ERROR)
    return handler


def configure_logging() -> None:
    timestamper = structlog.processors.TimeStamper(fmt="iso")
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
    ]

    renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=renderer,
        foreign_pre_chain=shared_processors,
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    error_file_handler = _build_error_log_handler(
        log_dir=settings.log_path,
        retention_days=settings.error_log_retention_days,
    )
    error_file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
        handler.close()

    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(stream_handler)
    root_logger.addHandler(error_file_handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.propagate = True

