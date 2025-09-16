from __future__ import annotations

from datetime import datetime

import pytest

from optima_sim.core.entities import (
    Activity,
    Building,
    Floor,
    Location,
    LocationType,
    Resident,
    Unit,
)
from optima_sim.core.schedule import ScheduleEvent
from optima_sim.core.simulation import ELEVATOR_X, Simulation


def build_test_simulation() -> tuple[Simulation, Resident]:
    floor_l = Floor(floor_number=0, label="L", units=[])
    unit = Unit(unit_number="0501", floor=5, bedrooms=1, square_feet=900, rent=2800, position=0.22)
    floor_5 = Floor(floor_number=5, label="05", units=[unit])
    building = Building(
        name="Test Tower",
        address="Nowhere",
        floors=[floor_l, floor_5],
        amenities={},
    )

    home = Location(LocationType.UNIT, unit.unit_number, floor=5, x=unit.position)
    street = Location(LocationType.OUTSIDE, "Street", floor=0, x=0.18)

    schedule = [
        ScheduleEvent(0, 10, Activity.SLEEP, home, "Sleep"),
        ScheduleEvent(10, 20, Activity.COMMUTE, street, "Commute to street"),
        ScheduleEvent(20, 40, Activity.AWAY, street, "Out and about"),
        ScheduleEvent(40, 50, Activity.COMMUTE, home, "Return home"),
        ScheduleEvent(50, 1440, Activity.SLEEP, home, "Sleep"),
    ]

    resident = Resident(
        resident_id="test-resident",
        name="Test Resident",
        age=30,
        occupation="Engineer",
        persona="urban_professional",
        home_unit=unit,
        schedule=schedule,
    )
    unit.add_resident(resident)

    sim = Simulation(
        building,
        residents=[resident],
        start_time=datetime(2024, 1, 1, 0, 0),
        tick_minutes=1,
    )
    return sim, resident


def advance_until(sim: Simulation, resident: Resident, predicate, limit: int = 500) -> None:
    for _ in range(limit):
        sim.step()
        runtime = sim.runtime[resident.resident_id]
        if predicate(runtime, sim):
            return
    pytest.fail("Condition not met within simulation step limit")


def test_resident_waits_for_and_boards_elevator():
    sim, resident = build_test_simulation()

    def waiting(runtime, _sim):
        return runtime.status == "waiting_elevator"

    advance_until(sim, resident, waiting)
    runtime = sim.runtime[resident.resident_id]
    assert runtime.elevator_request is not None
    assert runtime.floor == resident.home_unit.floor
    assert pytest.approx(runtime.x, rel=1e-3) == runtime.target_x

    def boarded(runtime, _sim):
        return runtime.status == "in_elevator"

    advance_until(sim, resident, boarded)
    runtime = sim.runtime[resident.resident_id]
    assert runtime.elevator_request is None
    assert runtime.location_label == "Elevator"
    assert runtime.x == pytest.approx(ELEVATOR_X, rel=1e-3)
    assert runtime.target_x == pytest.approx(ELEVATOR_X, rel=1e-3)
    assert runtime.vertical_position == pytest.approx(sim.elevator.position, rel=1e-6)


def test_resident_exits_at_destination():
    sim, resident = build_test_simulation()

    def reached_street(runtime, _sim):
        return runtime.location_label == "Street" and runtime.status == "in_event"

    advance_until(sim, resident, reached_street)
    runtime = sim.runtime[resident.resident_id]
    assert runtime.floor == 0
    assert runtime.location_type == LocationType.OUTSIDE
    assert runtime.status == "in_event"
    assert runtime.destination is not None
    assert runtime.destination.label == "Street"


def test_elevator_moves_smoothly():
    sim, resident = build_test_simulation()

    positions: list[float] = []

    def capture_motion(runtime, sim_obj):
        positions.append(sim_obj.elevator.position)
        return runtime.status == "in_event" and runtime.location_label == "Street"

    advance_until(sim, resident, capture_motion)

    deltas = [abs(n - p) for p, n in zip(positions, positions[1:])]
    smooth_limit = sim.elevator.speed + 1e-6
    assert deltas, "Elevator never moved"
    assert all(delta <= smooth_limit for delta in deltas)
