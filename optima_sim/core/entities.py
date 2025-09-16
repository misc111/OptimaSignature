"""Domain entities for the Optima Signature simulation."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class Activity(Enum):
    """High-level activities that residents perform throughout the day."""

    SLEEP = "sleep"
    WORK = "work"
    COMMUTE = "commute"
    AMENITY = "amenity"
    EAT = "eat"
    ERRAND = "errand"
    LEISURE = "leisure"
    AT_HOME = "at_home"
    AWAY = "away"


class LocationType(Enum):
    """Types of locations residents can occupy."""

    UNIT = "unit"
    AMENITY = "amenity"
    OUTSIDE = "outside"
    SERVICE = "service"


@dataclass(frozen=True)
class Location:
    """Physical or logical place where a resident can be."""

    type: LocationType
    label: str
    floor: Optional[int] = None
    x: Optional[float] = None


@dataclass
class Amenity:
    name: str
    floor: int
    capacity: int
    category: str
    open_minute: int = 0
    close_minute: int = 1440
    metadata: Dict[str, str] = field(default_factory=dict)
    x: float = 0.5

    def is_open(self, minute_of_day: int) -> bool:
        return self.open_minute <= minute_of_day < self.close_minute


@dataclass
class Unit:
    unit_number: str
    floor: int
    bedrooms: int
    square_feet: int
    rent: int
    position: float
    residents: List["Resident"] = field(default_factory=list)

    def add_resident(self, resident: "Resident") -> None:
        self.residents.append(resident)


@dataclass
class Floor:
    floor_number: int
    label: str
    units: List[Unit] = field(default_factory=list)
    amenities: List[Amenity] = field(default_factory=list)

    def get_unit(self, unit_number: str) -> Optional[Unit]:
        return next((unit for unit in self.units if unit.unit_number == unit_number), None)


@dataclass
class Resident:
    """Represents a simulated resident living in the building."""

    resident_id: str
    name: str
    age: int
    occupation: str
    persona: str
    home_unit: Unit
    schedule: List["ScheduleEvent"]
    preferences: Dict[str, float] = field(default_factory=dict)
    mood: float = 0.5
    hair_color: str = "#ffffff"
    outfit_color: str = "#cccccc"
    accent_color: str = "#888888"

    _current_event_index: int = 0

    def current_event(self) -> "ScheduleEvent":
        return self.schedule[self._current_event_index]

    def advance_to_minute(self, minute: int) -> None:
        """Ensure the active event covers the provided minute."""
        schedule_len = len(self.schedule)
        if schedule_len == 0:
            return

        # Fast path if minute is within current event
        event = self.schedule[self._current_event_index]
        if event.start_minute <= minute < event.end_minute:
            return

        # Otherwise search linearly (schedule lists are short per day)
        for idx, candidate in enumerate(self.schedule):
            if candidate.start_minute <= minute < candidate.end_minute:
                self._current_event_index = idx
                return
        # If the minute is after the final event (e.g., due to wrap), reset
        self._current_event_index = schedule_len - 1


@dataclass
class Building:
    name: str
    address: str
    floors: List[Floor]
    amenities: Dict[str, Amenity]

    def get_floor(self, floor_number: int) -> Optional[Floor]:
        return next((floor for floor in self.floors if floor.floor_number == floor_number), None)

    def all_units(self) -> List[Unit]:
        return [unit for floor in self.floors for unit in floor.units]

    def all_residents(self) -> List[Resident]:
        return [resident for unit in self.all_units() for resident in unit.residents]


# Circular import safe type hints
from .schedule import ScheduleEvent  # noqa: E402  (placed at end to avoid circularity)
