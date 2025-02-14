import logging
import os
from contextvars import ContextVar, Token
from logging.config import dictConfig
from typing import Optional

_request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def set_request_id(value: str) -> Token:
    return _request_id_var.set(value or "-")


def reset_request_id(token: Token) -> None:
    _request_id_var.reset(token)


def get_request_id() -> str:
    return _request_id_var.get()


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        return True


def setup_logging(level: Optional[str] = None) -> None:
    level_value = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_id": {"()": "app.core.app_logging.RequestIdFilter"},
            },
            "formatters": {
                "default": {
                    "format": "%(asctime)s | %(levelname)s | %(name)s | %(request_id)s | %(message)s"
                }
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["request_id"],
                }
            },
            "root": {"level": level_value, "handlers": ["default"]},
        }
    )
