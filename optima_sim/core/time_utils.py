"""Helper functions for working with simulation time."""
from __future__ import annotations

from datetime import datetime, timedelta

MINUTES_PER_DAY = 24 * 60


def minute_of_day(dt: datetime) -> int:
    return dt.hour * 60 + dt.minute


def advance_time(dt: datetime, minutes: int) -> datetime:
    return dt + timedelta(minutes=minutes)


def add_minutes(minute: int, delta: int) -> int:
    """Return minute-of-day after adding delta, wrapping around the day."""
    return (minute + delta) % MINUTES_PER_DAY


def clamp_day(minute: int) -> int:
    return minute % MINUTES_PER_DAY
