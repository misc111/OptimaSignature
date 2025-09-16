"""Schedule primitives for residents."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List

from .entities import Activity, Location


@dataclass
class ScheduleEvent:
    start_minute: int
    end_minute: int
    activity: Activity
    location: Location
    label: str

    def contains(self, minute: int) -> bool:
        return self.start_minute <= minute < self.end_minute

    def duration(self) -> int:
        return self.end_minute - self.start_minute


def merge_events(events: Iterable[ScheduleEvent]) -> List[ScheduleEvent]:
    """Merge adjacent events with matching activity and location."""
    sorted_events = sorted(events, key=lambda e: e.start_minute)
    merged: List[ScheduleEvent] = []
    for event in sorted_events:
        if not merged:
            merged.append(event)
            continue
        prev = merged[-1]
        if (
            prev.activity == event.activity
            and prev.location == event.location
            and prev.end_minute == event.start_minute
        ):
            merged[-1] = ScheduleEvent(
                start_minute=prev.start_minute,
                end_minute=event.end_minute,
                activity=prev.activity,
                location=prev.location,
                label=prev.label,
            )
        else:
            merged.append(event)
    return merged


def minutes_to_clock(minute: int) -> str:
    minute = minute % 1440
    hour = minute // 60
    mins = minute % 60
    suffix = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour:02d}:{mins:02d} {suffix}"
