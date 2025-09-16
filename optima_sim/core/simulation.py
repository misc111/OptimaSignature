"""Core simulation loop for Optima Signature with elevator logistics and visuals."""
from __future__ import annotations

import math
from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Deque, Dict, Iterable, List, Optional, Tuple

from .entities import Activity, Building, Location, LocationType, Resident
from .schedule import minutes_to_clock
from .time_utils import advance_time, minute_of_day

ELEVATOR_X = 0.5
ELEVATOR_WAIT_X = 0.45
WALK_SPEED = 0.18
SUNRISE = 6 * 60
SUNSET = 19 * 60


@dataclass
class ResidentRuntime:
    resident: Resident
    floor: int
    vertical_position: float
    x: float
    target_x: float
    status: str
    location_label: str
    location_type: LocationType
    destination: Optional[Location] = None
    pending_event_label: Optional[str] = None
    pending_activity: Activity = Activity.AT_HOME
    elevator_request: Optional["ElevatorRequest"] = None
    last_event_index: int = 0
    ticks_in_status: int = 0
    travel_destination_floor: Optional[int] = None


@dataclass
class ResidentSnapshot:
    resident_id: str
    name: str
    persona: str
    activity: Activity
    location: str
    floor: int
    floor_label: str
    location_type: LocationType
    mood: float
    x: float
    target_x: float
    status: str
    vertical_position: float
    hair_color: str
    outfit_color: str
    accent_color: str


@dataclass
class SimulationEvent:
    timestamp: datetime
    resident_name: str
    description: str
    location: str


@dataclass
class ElevatorRequest:
    resident_id: str
    origin: int
    destination: int
    direction: int
    created_tick: int


@dataclass
class ElevatorPassenger:
    resident_id: str
    destination: int


@dataclass
class ElevatorStepOutcome:
    boarded: List[str]
    disembarked: List[Tuple[str, int]]
    position: float
    doors_open: bool
    floor: int


class ElevatorSystem:
    def __init__(
        self,
        min_floor: int,
        max_floor: int,
        capacity: int = 10,
        speed_per_tick: float = 0.5,
    ) -> None:
        self.min_floor = min_floor
        self.max_floor = max_floor
        self.capacity = capacity
        self.speed = speed_per_tick
        self.position = float(min_floor)
        self.state: str = "idle"
        self.target_floor: Optional[int] = None
        self.waiting: Dict[int, Deque[ElevatorRequest]] = defaultdict(deque)
        self.pending: Dict[str, ElevatorRequest] = {}
        self.passengers: List[ElevatorPassenger] = []
        self.direction: int = 0
        self.door_timer: int = 0

    def request(self, resident_id: str, origin: int, destination: int, tick: int) -> ElevatorRequest:
        existing = self.pending.get(resident_id)
        if existing:
            return existing
        if any(p.resident_id == resident_id for p in self.passengers):
            return ElevatorRequest(resident_id, origin, destination, 1 if destination > origin else -1, tick)
        direction = 1 if destination > origin else -1
        request = ElevatorRequest(resident_id, origin, destination, direction, tick)
        self.waiting[origin].append(request)
        self.pending[resident_id] = request
        if self.state == "idle" and self.target_floor is None:
            self._choose_next_target()
        return request

    def _choose_next_target(self) -> bool:
        current_floor = int(round(self.position))
        # Prioritize passenger drop-offs first
        if self.passengers:
            destinations = [p.destination for p in self.passengers]
            nearest = min(destinations, key=lambda fl: abs(fl - self.position))
            self.target_floor = nearest
            if self.target_floor == current_floor:
                return True
            self.state = "moving"
            self.direction = 1 if self.target_floor > self.position else -1
            return True

        waiting_floors = [floor for floor, queue in self.waiting.items() if queue]
        if not waiting_floors:
            self.target_floor = None
            self.state = "idle"
            self.direction = 0
            return False

        nearest = min(waiting_floors, key=lambda fl: abs(fl - self.position))
        self.target_floor = nearest
        if self.target_floor == current_floor:
            return True
        self.state = "moving"
        self.direction = 1 if self.target_floor > self.position else -1
        return True

    def _has_service_here(self, floor: int) -> bool:
        if any(p.destination == floor for p in self.passengers):
            return True
        queue = self.waiting.get(floor)
        return bool(queue)

    def _arrive(self, floor: int) -> Tuple[List[str], List[Tuple[str, int]]]:
        boarded: List[str] = []
        disembarked: List[Tuple[str, int]] = []

        # Drop off passengers first
        remaining_passengers: List[ElevatorPassenger] = []
        for passenger in self.passengers:
            if passenger.destination == floor:
                disembarked.append((passenger.resident_id, floor))
            else:
                remaining_passengers.append(passenger)
        self.passengers = remaining_passengers

        # Board waiting residents
        queue = self.waiting.get(floor)
        if queue:
            while queue and len(self.passengers) < self.capacity:
                request = queue.popleft()
                boarded.append(request.resident_id)
                self.passengers.append(ElevatorPassenger(request.resident_id, request.destination))
                self.pending.pop(request.resident_id, None)
            if not queue:
                self.waiting.pop(floor, None)

        self.state = "door_open"
        self.door_timer = 1
        self.direction = 0
        self.target_floor = None
        return boarded, disembarked

    def step(self) -> ElevatorStepOutcome:
        boarded: List[str] = []
        disembarked: List[Tuple[str, int]] = []
        doors_open = False
        current_floor = int(round(self.position))

        if self.state == "door_open":
            doors_open = True
            if self.door_timer > 0:
                self.door_timer -= 1
            if self.door_timer <= 0:
                self.state = "idle"
                self._choose_next_target()
            return ElevatorStepOutcome(boarded, disembarked, self.position, doors_open, current_floor)

        if self.state == "idle":
            if self._has_service_here(current_floor):
                doors_open = True
                boarded, disembarked = self._arrive(current_floor)
                return ElevatorStepOutcome(boarded, disembarked, self.position, doors_open, current_floor)
            if not self._choose_next_target():
                return ElevatorStepOutcome(boarded, disembarked, self.position, doors_open, current_floor)

        if self.state == "moving" and self.target_floor is not None:
            step = self.speed if self.target_floor > self.position else -self.speed
            next_position = self.position + step
            arrived = (
                (step > 0 and next_position >= self.target_floor)
                or (step < 0 and next_position <= self.target_floor)
            )
            if arrived:
                self.position = float(self.target_floor)
                current_floor = int(round(self.position))
                doors_open = True
                boarded, disembarked = self._arrive(current_floor)
            else:
                self.position = max(self.min_floor, min(self.max_floor, next_position))
            return ElevatorStepOutcome(boarded, disembarked, self.position, doors_open, current_floor)

        return ElevatorStepOutcome(boarded, disembarked, self.position, doors_open, current_floor)

    def waiting_counts(self) -> Dict[int, int]:
        return {floor: len(queue) for floor, queue in self.waiting.items() if queue}


class Simulation:
    def __init__(
        self,
        building: Building,
        residents: Iterable[Resident],
        start_time: datetime | None = None,
        tick_minutes: int = 1,
    ) -> None:
        self.building = building
        self.residents = list(residents)
        self.tick_minutes = tick_minutes
        self.current_time = start_time or datetime(2024, 1, 1, 6, 0)
        self.minute_of_day = minute_of_day(self.current_time)
        self.events: Deque[SimulationEvent] = deque(maxlen=300)
        self._tick_counter = 0
        self.runtime: Dict[str, ResidentRuntime] = {}
        max_floor = max((floor.floor_number for floor in self.building.floors), default=0)
        self.elevator = ElevatorSystem(min_floor=0, max_floor=max_floor)
        self.building_outline = self._build_outline()

        for resident in self.residents:
            resident.advance_to_minute(self.minute_of_day)
            home_location = Location(
                LocationType.UNIT,
                resident.home_unit.unit_number,
                floor=resident.home_unit.floor,
                x=resident.home_unit.position,
            )
            runtime = ResidentRuntime(
                resident=resident,
                floor=resident.home_unit.floor,
                vertical_position=float(resident.home_unit.floor),
                x=resident.home_unit.position,
                target_x=resident.home_unit.position,
                status="in_event",
                location_label=home_location.label,
                location_type=LocationType.UNIT,
                destination=None,
                pending_event_label=None,
                pending_activity=resident.current_event().activity if resident.schedule else Activity.AT_HOME,
                elevator_request=None,
                last_event_index=resident._current_event_index,
                ticks_in_status=0,
                travel_destination_floor=None,
            )
            runtime.destination = home_location
            runtime.pending_event_label = resident.current_event().label if resident.schedule else "Idle"
            self.runtime[resident.resident_id] = runtime

    def step(self) -> None:
        self.current_time = advance_time(self.current_time, self.tick_minutes)
        self.minute_of_day = minute_of_day(self.current_time)
        self._tick_counter += 1

        for resident in self.residents:
            resident.advance_to_minute(self.minute_of_day)
            runtime = self.runtime[resident.resident_id]
            event = resident.current_event()
            if resident._current_event_index != runtime.last_event_index:
                runtime.pending_event_label = event.label
                runtime.pending_activity = event.activity
                runtime.last_event_index = resident._current_event_index
                runtime.destination = event.location
                if runtime.status == "in_event" and self._reached_destination(runtime, event.location):
                    runtime.status = "in_event"
                    runtime.location_label = event.location.label
                    runtime.location_type = event.location.type
                    runtime.target_x = event.location.x or runtime.x
                    runtime.x = runtime.target_x
                    self._log_event(resident, event.label, event.location.label)
            self._update_resident_target(runtime, event.location)

        outcome = self.elevator.step()
        if outcome.boarded or outcome.disembarked:
            for resident_id in outcome.boarded:
                runtime = self.runtime[resident_id]
                runtime.status = "in_elevator"
                runtime.ticks_in_status = 0
                runtime.location_label = "Elevator"
                runtime.location_type = LocationType.SERVICE
                runtime.vertical_position = outcome.position
                runtime.floor = outcome.floor
                runtime.x = ELEVATOR_X
                runtime.target_x = ELEVATOR_X
                runtime.elevator_request = None
                if runtime.pending_event_label:
                    destination_floor = runtime.travel_destination_floor or runtime.floor
                    label = self._format_floor(destination_floor)
                    self._log_event(runtime.resident, f"Boarded elevator to {label}", "Elevator")

            for resident_id, floor in outcome.disembarked:
                runtime = self.runtime[resident_id]
                runtime.status = "walking"
                runtime.ticks_in_status = 0
                runtime.location_label = "Elevator Lobby"
                runtime.location_type = LocationType.SERVICE
                runtime.floor = floor
                runtime.vertical_position = float(floor)
                runtime.x = ELEVATOR_WAIT_X
                runtime.target_x = (
                    runtime.destination.x if runtime.destination and runtime.destination.x is not None else runtime.x
                )
                runtime.elevator_request = None
                runtime.travel_destination_floor = None
                self._log_event(runtime.resident, f"Arrived on floor {self._format_floor(floor)}", "Elevator Lobby")

        for runtime in self.runtime.values():
            runtime.ticks_in_status += 1
            if runtime.status == "in_elevator":
                runtime.vertical_position = outcome.position
                runtime.floor = outcome.floor
                runtime.x = ELEVATOR_X
            elif runtime.status in {"waiting_elevator", "walking"}:
                self._nudge_position(runtime)
            elif runtime.status == "in_event" and runtime.destination and runtime.destination.x is not None:
                runtime.x = runtime.destination.x
                runtime.target_x = runtime.destination.x

            current_activity = (
                runtime.pending_activity if runtime.status == "in_event" else Activity.COMMUTE
            )
            self._adjust_mood(runtime.resident, current_activity)

            if runtime.status == "walking" and runtime.destination:
                if self._reached_destination(runtime, runtime.destination):
                    runtime.status = "in_event"
                    runtime.location_label = runtime.destination.label
                    runtime.location_type = runtime.destination.type
                    runtime.floor = runtime.destination.floor or runtime.floor
                    runtime.vertical_position = float(runtime.floor)
                    runtime.x = runtime.destination.x or runtime.x
                    runtime.target_x = runtime.x
                    if runtime.pending_event_label:
                        self._log_event(
                            runtime.resident,
                            runtime.pending_event_label,
                            runtime.destination.label,
                        )
                        runtime.pending_event_label = None
            if runtime.status == "waiting_elevator":
                runtime.x = self._approach(runtime.x, ELEVATOR_WAIT_X)
                runtime.target_x = ELEVATOR_WAIT_X

    def run_ticks(self, count: int) -> None:
        for _ in range(count):
            self.step()

    def state_snapshot(self) -> Dict[str, object]:
        activity_counter: Counter[str] = Counter()
        amenity_load: Dict[str, int] = Counter()
        resident_states: List[ResidentSnapshot] = []

        for runtime in self.runtime.values():
            resident = runtime.resident
            event = resident.current_event()
            activity = event.activity if runtime.status == "in_event" else Activity.COMMUTE
            activity_counter[activity.value] += 1
            if runtime.location_type == LocationType.AMENITY and runtime.status == "in_event":
                amenity_load[runtime.location_label] += 1
            resident_states.append(
                ResidentSnapshot(
                    resident_id=resident.resident_id,
                    name=resident.name,
                    persona=resident.persona,
                    activity=activity,
                    location=runtime.location_label,
                    floor=runtime.floor,
                    floor_label=self._format_floor(runtime.floor),
                    location_type=runtime.location_type,
                    mood=round(resident.mood, 2),
                    x=round(runtime.x, 3),
                    target_x=round(runtime.target_x, 3),
                    status=runtime.status,
                    vertical_position=round(runtime.vertical_position, 3),
                    hair_color=resident.hair_color,
                    outfit_color=resident.outfit_color,
                    accent_color=resident.accent_color,
                )
            )

        sunlight = self._sunlight_state()

        return {
            "timestamp": self.current_time.isoformat(),
            "minute_of_day": self.minute_of_day,
            "clock": minutes_to_clock(self.minute_of_day),
            "activity_breakdown": dict(activity_counter),
            "amenity_load": dict(amenity_load),
            "residents": [
                {
                    "resident_id": snapshot.resident_id,
                    "name": snapshot.name,
                    "persona": snapshot.persona,
                    "activity": snapshot.activity.value,
                    "location": snapshot.location,
                    "location_type": snapshot.location_type.value,
                    "floor": snapshot.floor,
                    "floor_label": snapshot.floor_label,
                    "mood": snapshot.mood,
                    "x": snapshot.x,
                    "target_x": snapshot.target_x,
                    "status": snapshot.status,
                    "vertical_position": snapshot.vertical_position,
                    "hair_color": snapshot.hair_color,
                    "outfit_color": snapshot.outfit_color,
                    "accent_color": snapshot.accent_color,
                }
                for snapshot in resident_states
            ],
            "events": [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "resident": event.resident_name,
                    "description": event.description,
                    "location": event.location,
                }
                for event in list(self.events)
            ],
            "tick": self._tick_counter,
            "sunlight": sunlight,
            "elevator": {
                "position": round(self.elevator.position, 3),
                "floor": int(round(self.elevator.position)),
                "doors_open": self.elevator.state == "door_open",
                "passengers": len(self.elevator.passengers),
                "waiting": self.elevator.waiting_counts(),
            },
            "building": self.building_outline,
        }

    # --- Internal helpers -------------------------------------------------
    def _update_resident_target(self, runtime: ResidentRuntime, destination: Location) -> None:
        if runtime.status == "in_event" and self._reached_destination(runtime, destination):
            runtime.destination = destination
            runtime.target_x = destination.x or runtime.x
            runtime.x = runtime.target_x
            return

        runtime.destination = destination
        if runtime.status == "in_elevator":
            runtime.target_x = ELEVATOR_X
            runtime.x = ELEVATOR_X
            return
        dest_floor = destination.floor if destination.floor is not None else runtime.floor
        if dest_floor != runtime.floor:
            if runtime.elevator_request is None:
                runtime.status = "waiting_elevator"
                runtime.ticks_in_status = 0
                runtime.location_label = "Elevator Lobby"
                runtime.location_type = LocationType.SERVICE
                runtime.target_x = ELEVATOR_WAIT_X
                runtime.elevator_request = self.elevator.request(
                    runtime.resident.resident_id,
                    origin=runtime.floor,
                    destination=dest_floor,
                    tick=self._tick_counter,
                )
                runtime.travel_destination_floor = dest_floor
                label = self._format_floor(dest_floor)
                self._log_event(runtime.resident, f"Waiting for elevator to {label}", "Elevator Lobby")
        else:
            if runtime.status != "in_event":
                runtime.status = "walking"
                runtime.ticks_in_status = 0
            runtime.location_label = "Corridor"
            runtime.location_type = LocationType.SERVICE
            runtime.target_x = destination.x or runtime.target_x
            runtime.travel_destination_floor = None
            runtime.elevator_request = None

    def _nudge_position(self, runtime: ResidentRuntime) -> None:
        runtime.x = self._approach(runtime.x, runtime.target_x)

    @staticmethod
    def _approach(current: float, target: float) -> float:
        if abs(current - target) <= WALK_SPEED:
            return target
        step = WALK_SPEED if target > current else -WALK_SPEED
        return round(current + step, 3)

    def _reached_destination(self, runtime: ResidentRuntime, location: Location) -> bool:
        target_floor = location.floor if location.floor is not None else runtime.floor
        if runtime.floor != target_floor:
            return False
        if location.x is not None and abs(runtime.x - location.x) > 0.05:
            return False
        return True

    def _build_outline(self) -> List[Dict[str, object]]:
        outline: List[Dict[str, object]] = []
        for floor in sorted(self.building.floors, key=lambda f: f.floor_number):
            outline.append(
                {
                    "floor": floor.floor_number,
                    "label": floor.label,
                    "units": [
                        {
                            "unit": unit.unit_number,
                            "position": unit.position,
                            "bedrooms": unit.bedrooms,
                            "width": unit.width,
                            "depth": unit.depth,
                            "room_type": unit.room_type,
                        }
                        for unit in floor.units
                    ],
                    "amenities": [],
                }
            )
        return outline

    def _format_floor(self, floor: int) -> str:
        floor_obj = self.building.get_floor(floor)
        if floor_obj:
            return floor_obj.label
        return str(floor)

    def _log_event(self, resident: Resident, description: str, location: str) -> None:
        self.events.append(
            SimulationEvent(
                timestamp=self.current_time,
                resident_name=resident.name,
                description=description,
                location=location,
            )
        )

    def _adjust_mood(self, resident: Resident, activity: Activity) -> None:
        delta = 0.0
        if activity == Activity.AMENITY:
            delta = 0.01
        elif activity == Activity.COMMUTE:
            delta = -0.003
        elif activity == Activity.WORK:
            delta = -0.0015
        elif activity == Activity.LEISURE:
            delta = 0.004
        elif activity == Activity.SLEEP:
            delta = 0.002
        resident.mood = max(0.0, min(1.0, resident.mood + delta))

    def _sunlight_state(self) -> Dict[str, float | bool]:
        minute = self.minute_of_day
        if SUNRISE <= minute <= SUNSET:
            progress = (minute - SUNRISE) / (SUNSET - SUNRISE)
            angle = progress * math.pi
            brightness = 0.25 + 0.75 * math.sin(angle)
            sun_altitude = math.sin(angle)
            return {
                "is_day": True,
                "sun_altitude": round(sun_altitude, 3),
                "brightness": round(brightness, 3),
            }
        if minute < SUNRISE:
            span = SUNRISE + (1440 - SUNSET)
            progress = (minute + (1440 - SUNSET)) / span
        else:
            span = SUNRISE + (1440 - SUNSET)
            progress = (minute - SUNSET) / span
        angle = progress * math.pi
        brightness = 0.05 + 0.25 * math.sin(angle)
        sun_altitude = -math.sin(angle)
        return {
            "is_day": False,
            "sun_altitude": round(sun_altitude, 3),
            "brightness": round(brightness, 3),
        }
