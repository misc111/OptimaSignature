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
    amenity_list = [
        Amenity(
            name="Fitness Center",
            floor=1,
            capacity=20,
            category="fitness",
            x=0.2,
            metadata={"room_type": "unit_standard"},
        ),
        Amenity(
            name="Rooftop Pool",
            floor=10,
            capacity=15,
            category="pool",
            x=0.8,
            metadata={"room_type": "unit_standard"},
        ),
        Amenity(
            name="Resident Lounge",
            floor=1,
            capacity=25,
            category="lounge",
            x=0.8,
            metadata={"room_type": "unit_standard"},
        ),
        Amenity(
            name="Coworking Space",
            floor=2,
            capacity=18,
            category="workspace",
            x=0.2,
            metadata={"room_type": "unit_standard"},
        ),
        Amenity(
            name="Spa & Sauna",
            floor=2,
            capacity=8,
            category="spa",
            x=0.8,
            metadata={"room_type": "unit_standard"},
        ),
        Amenity(
            name="Playroom",
            floor=3,
            capacity=10,
            category="family",
            x=0.2,
            metadata={"room_type": "unit_standard"},
        ),
    ]
    return {amenity.name: amenity for amenity in amenity_list}


def load_building() -> Building:
    floors: List[Floor] = [Floor(floor_number=0, label="L", units=[])]

    for floor_number in range(1, 11):
        label = f"{floor_number:02d}"
        units = _create_units_for_floor(floor_number)
        floors.append(Floor(floor_number=floor_number, label=label, units=units))

    amenities = _amenities()

    return Building(
        name="Simplified Tower",
        address="123 Main St, Chicago, IL",
        floors=floors,
        amenities=amenities,
    )
