"""Static configuration describing the Optima Signature building."""
from __future__ import annotations

from typing import Dict, List

from ..core.entities import Amenity, Building, Floor, Unit


def _unit_layout() -> List[Dict[str, object]]:
    return [
        {
            "suffix": "01",
            "bedrooms": 1,
            "sqft": 910,
            "rent": 3300,
            "position": 0.1,
            "width": 0.18,
            "depth": 0.24,
            "room_type": "unit_1br",
        },
        {
            "suffix": "02",
            "bedrooms": 2,
            "sqft": 1290,
            "rent": 4950,
            "position": 0.32,
            "width": 0.2,
            "depth": 0.26,
            "room_type": "unit_2br",
        },
        {
            "suffix": "03",
            "bedrooms": 2,
            "sqft": 1350,
            "rent": 5100,
            "position": 0.56,
            "width": 0.2,
            "depth": 0.26,
            "room_type": "unit_2br",
        },
        {
            "suffix": "04",
            "bedrooms": 3,
            "sqft": 1680,
            "rent": 6550,
            "position": 0.78,
            "width": 0.22,
            "depth": 0.28,
            "room_type": "unit_3br",
        },
    ]


def _create_units_for_floor(floor_number: int) -> List[Unit]:
    units: List[Unit] = []
    for spec in _unit_layout():
        unit_number = f"{floor_number:02d}{spec['suffix']}"
        units.append(
            Unit(
                unit_number=unit_number,
                floor=floor_number,
                bedrooms=spec["bedrooms"],
                square_feet=spec["sqft"],
                rent=spec["rent"],
                position=float(spec["position"]),
                width=float(spec["width"]),
                depth=float(spec["depth"]),
                room_type=str(spec["room_type"]),
            )
        )
    return units


def _create_penthouse_floor() -> List[Unit]:
    return [
        Unit(
            unit_number="52PH",
            floor=52,
            bedrooms=4,
            square_feet=4200,
            rent=18500,
            position=0.55,
            width=0.28,
            depth=0.3,
            room_type="penthouse",
        )
    ]


def _amenities() -> Dict[str, Amenity]:
    amenities = [
        Amenity(
            name="Lobby Lounge",
            floor=0,
            capacity=60,
            category="lounge",
            open_minute=6 * 60,
            close_minute=23 * 60,
            x=0.48,
            metadata={"room_type": "lounge", "width": 0.38, "depth": 0.3},
        ),
        Amenity(
            name="Sky Pool",
            floor=8,
            capacity=75,
            category="pool",
            open_minute=6 * 60,
            close_minute=22 * 60,
            x=0.7,
            metadata={"room_type": "pool", "width": 0.4, "depth": 0.32},
        ),
        Amenity(
            name="Fitness Center",
            floor=7,
            capacity=60,
            category="fitness",
            open_minute=5 * 60,
            close_minute=23 * 60,
            x=0.3,
            metadata={"room_type": "fitness", "width": 0.42, "depth": 0.32},
        ),
        Amenity(
            name="Coworking Lounge",
            floor=9,
            capacity=50,
            category="workspace",
            open_minute=7 * 60,
            close_minute=22 * 60,
            x=0.62,
            metadata={"room_type": "workspace", "width": 0.38, "depth": 0.3},
        ),
        Amenity(
            name="Basketball Court",
            floor=10,
            capacity=30,
            category="sports",
            open_minute=8 * 60,
            close_minute=22 * 60,
            x=0.4,
            metadata={"room_type": "fitness", "width": 0.5, "depth": 0.34},
        ),
        Amenity(
            name="Spa",
            floor=7,
            capacity=12,
            category="spa",
            open_minute=10 * 60,
            close_minute=21 * 60,
            x=0.75,
            metadata={"room_type": "spa", "width": 0.28, "depth": 0.28},
        ),
        Amenity(
            name="Children's Playroom",
            floor=8,
            capacity=20,
            category="family",
            open_minute=8 * 60,
            close_minute=20 * 60,
            x=0.25,
            metadata={"room_type": "family", "width": 0.32, "depth": 0.3},
        ),
        Amenity(
            name="Retreat Lounge",
            floor=20,
            capacity=45,
            category="lounge",
            open_minute=9 * 60,
            close_minute=24 * 60,
            x=0.6,
            metadata={"room_type": "lounge", "width": 0.36, "depth": 0.3},
        ),
        Amenity(
            name="Skyline Lounge",
            floor=52,
            capacity=35,
            category="lounge",
            open_minute=10 * 60,
            close_minute=24 * 60,
            x=0.32,
            metadata={"room_type": "lounge", "width": 0.4, "depth": 0.3},
        ),
        Amenity(
            name="Cafe Optima",
            floor=0,
            capacity=25,
            category="dining",
            open_minute=6 * 60,
            close_minute=20 * 60,
            x=0.62,
            metadata={"room_type": "dining", "width": 0.34, "depth": 0.28},
        ),
    ]
    return {amenity.name: amenity for amenity in amenities}


def load_building() -> Building:
    floors: List[Floor] = []
    for floor_number in range(0, 53):
        label = "L" if floor_number == 0 else f"{floor_number:02d}"
        if floor_number == 52:
            units = _create_penthouse_floor()
        elif 1 <= floor_number <= 51:
            units = _create_units_for_floor(floor_number)
        else:
            units = []
        floor = Floor(floor_number=floor_number, label=label, units=units)
        floors.append(floor)

    amenities = _amenities()
    for amenity in amenities.values():
        floor = next((f for f in floors if f.floor_number == amenity.floor), None)
        if floor:
            floor.amenities.append(amenity)

    return Building(
        name="Optima Signature",
        address="220 E Illinois St, Chicago, IL 60611",
        floors=floors,
        amenities=amenities,
    )
