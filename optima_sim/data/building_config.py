"""Static configuration describing the Optima Signature building."""
from __future__ import annotations

from typing import Dict, List

from ..core.entities import Amenity, Building, Floor, Unit


def _unit_layout() -> List[Dict[str, object]]:
    return [
        {
            "suffix": "01",
            "bedrooms": 2,
            "sqft": 1050,
            "rent": 3800,
            "position": 0.2,
            "width": 0.28,
            "depth": 0.25,
            "room_type": "unit_standard",
        },
        {
            "suffix": "02",
            "bedrooms": 2,
            "sqft": 1050,
            "rent": 3800,
            "position": 0.5,
            "width": 0.28,
            "depth": 0.25,
            "room_type": "unit_standard",
        },
        {
            "suffix": "03",
            "bedrooms": 2,
            "sqft": 1050,
            "rent": 3800,
            "position": 0.8,
            "width": 0.28,
            "depth": 0.25,
            "room_type": "unit_standard",
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


def _amenities() -> Dict[str, Amenity]:
    return {}


def load_building() -> Building:
    floors: List[Floor] = []
    for index, floor_number in enumerate(range(1, 11)):
        label = f"{floor_number:02d}"
        units = _create_units_for_floor(floor_number)
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
