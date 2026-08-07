"""Injectable UTC wall-clock for deterministic scheduling tests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

ClockProvider = Callable[[], datetime]

_provider: ClockProvider | None = None


def utc_now() -> datetime:
    """Return timezone-aware UTC now (overridable via :func:`set_clock_provider`)."""
    if _provider is not None:
        value = _provider()
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return datetime.now(timezone.utc)


def set_clock_provider(provider: ClockProvider | None) -> None:
    """Install or clear a process-wide clock provider (tests only)."""
    global _provider
    _provider = provider


def reset_clock_provider() -> None:
    set_clock_provider(None)
