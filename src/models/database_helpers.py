"""Shared helpers for the SMS application database layer."""

from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any, TypeVar, cast

DB_TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"

_F = TypeVar("_F", bound=Callable[..., Any])


class DatabaseError(Exception):
    """Raised when the database cannot be initialized or accessed."""


def format_db_timestamp(value: datetime | str) -> str:
    """Format a datetime or string for SQLite TEXT timestamp columns."""
    if isinstance(value, datetime):
        return value.strftime(DB_TIMESTAMP_FORMAT)
    return value


def db_locked(method: _F) -> _F:
    """Run a database method under the instance reentrant lock."""

    @wraps(method)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        with self._lock:  # pylint: disable=protected-access
            return method(self, *args, **kwargs)

    return cast(_F, wrapper)
