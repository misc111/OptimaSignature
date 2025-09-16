"""Resident personas and schedule generation."""
from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Tuple

from ..core.entities import (
    Activity,
    Amenity,
    Building,
    Location,
    LocationType,
    Resident,
    Unit,
)
from ..core.schedule import ScheduleEvent, merge_events

FirstNames = [
    "Avery",
    "Jordan",
    "Morgan",
    "Taylor",
    "Cameron",
    "Riley",
    "Casey",
    "Sydney",
    "Devon",
    "Elliot",
    "Kai",
    "Logan",
    "Micah",
    "Parker",
    "Reese",
    "Sage",
    "Skylar",
    "Rowan",
    "Hayden",
    "Quinn",
]

LastNames = [
    "Anderson",
    "Bennett",
    "Chen",
    "Das",
    "Edwards",
    "Fischer",
    "Garcia",
    "Hughes",
    "Ivanov",
    "Jackson",
    "Kim",
    "Liu",
    "Martinez",
    "Novak",
    "O'Neal",
    "Patel",
    "Rivera",
    "Singh",
    "Thompson",
    "Williams",
]


@dataclass
class PersonaProfile:
    name: str
    occupations: Tuple[str, ...]
    age_range: Tuple[int, int]
    schedule_builder: Callable[["ResidentFactory", Unit], List[ScheduleEvent]]
    amenity_preferences: Dict[str, float]


class ResidentFactory:
    def __init__(self, building: Building, seed: int | None = None) -> None:
        self.building = building
        self.rng = random.Random(seed)
        self._amenity_cache: Dict[str, List[Amenity]] = {}

    def populate_building(self, occupancy: float = 0.93) -> List[Resident]:
        residents: List[Resident] = []
        for unit in self.building.all_units():
            persona = self.rng.choice(PERSONA_PROFILES)
            resident = self._create_resident(unit, persona)
            unit.add_resident(resident)
            residents.append(resident)
        return residents

    def _create_resident(self, unit: Unit, persona: PersonaProfile) -> Resident:
        name = f"{self.rng.choice(FirstNames)} {self.rng.choice(LastNames)}"
        age = self.rng.randint(*persona.age_range)
        occupation = self.rng.choice(persona.occupations)
        schedule = persona.schedule_builder(self, unit)
        hair, outfit, accent = self._appearance_for(persona.name)
        resident = Resident(
            resident_id=str(uuid.uuid4()),
            name=name,
            age=age,
            occupation=occupation,
            persona=persona.name,
            home_unit=unit,
            schedule=schedule,
            preferences=persona.amenity_preferences,
            mood=self.rng.uniform(0.45, 0.55),
            hair_color=hair,
            outfit_color=outfit,
            accent_color=accent,
        )
        return resident

    # --- Schedule helpers -------------------------------------------------
    def _home_location(self, unit: Unit) -> Location:
        return Location(LocationType.UNIT, unit.unit_number, floor=unit.floor, x=unit.position)

    def _amenities_by_category(self, category: str) -> List[Amenity]:
        if not self.building.amenities:
            return []
        if category not in self._amenity_cache:
            self._amenity_cache[category] = [
                amenity
                for amenity in self.building.amenities.values()
                if amenity.category == category
            ]
        return self._amenity_cache[category]

    def choose_amenity(self, categories: Iterable[str]) -> Amenity:
        choices: List[Amenity] = []
        for category in categories:
            choices.extend(self._amenities_by_category(category))
        if not choices:
            dummy_location = Location(LocationType.UNIT, "Home", floor=0, x=0.5)
            return Amenity(
                name="In-Unit",
                floor=0,
                capacity=1,
                category="unit",
                metadata={"fallback": "true"},
            )
        return self.rng.choice(choices)

    def _work_location(self, unit: Unit) -> Location:
        # Abstracted as being outside the building in the downtown core.
        return Location(LocationType.OUTSIDE, "Office Tower", floor=0, x=0.1)

    def _outside_location(self, label: str) -> Location:
        return Location(LocationType.OUTSIDE, label, floor=0, x=0.15)

    def amenity_location(self, amenity: Amenity) -> Location:
        return Location(LocationType.AMENITY, amenity.name, floor=amenity.floor, x=amenity.x)

    def named_amenity(self, name: str) -> Amenity:
        if self.building.amenities and name in self.building.amenities:
            return self.building.amenities[name]
        fallback = Amenity(
            name=name,
            floor=0,
            capacity=1,
            category="unit",
            metadata={"fallback": "true"},
        )
        return fallback

    def _appearance_for(self, persona: str) -> Tuple[str, str, str]:
        palette = APPEARANCE_PALETTES.get(persona)
        if not palette:
            return ("#ffffff", "#94a3b8", "#22d3ee")
        hair = self.rng.choice(palette["hair"])
        outfit = self.rng.choice(palette["outfit"])
        accent = self.rng.choice(palette["accent"])
        return hair, outfit, accent


# --- Persona schedule builders --------------------------------------------

def _build_urban_professional(factory: ResidentFactory, unit: Unit) -> List[ScheduleEvent]:
    rng = factory.rng
    home = factory._home_location(unit)
    events: List[ScheduleEvent] = []

    wake = rng.randint(6 * 60 + 15, 7 * 60 + 15)
    events.append(ScheduleEvent(0, wake, Activity.SLEEP, home, "Sleep"))

    morning_routine = wake + rng.randint(25, 45)
    events.append(
        ScheduleEvent(wake, morning_routine, Activity.AT_HOME, home, "Morning routine")
    )

    commute_out = morning_routine + rng.randint(30, 45)
    events.append(
        ScheduleEvent(
            morning_routine,
            commute_out,
            Activity.COMMUTE,
            factory._outside_location("Commute to office"),
            "Commute",
        )
    )

    work_start = commute_out
    work_lunch = work_start + rng.randint(3 * 60 + 30, 4 * 60)
    events.append(
        ScheduleEvent(
            work_start,
            work_lunch,
            Activity.WORK,
            factory._work_location(unit),
            "Office work",
        )
    )

    lunch_end = work_lunch + 60
    events.append(
        ScheduleEvent(
            work_lunch,
            lunch_end,
            Activity.EAT,
            factory._outside_location("Lunch near office"),
            "Lunch",
        )
    )

    work_end = lunch_end + rng.randint(3 * 60 + 15, 4 * 60 + 15)
    events.append(
        ScheduleEvent(
            lunch_end,
            work_end,
            Activity.WORK,
            factory._work_location(unit),
            "Afternoon work",
        )
    )

    commute_home_end = work_end + rng.randint(30, 50)
    events.append(
        ScheduleEvent(
            work_end,
            commute_home_end,
            Activity.COMMUTE,
            factory._outside_location("Commute home"),
            "Commute home",
        )
    )

    if rng.random() < 0.65:
        amenity = factory.choose_amenity(["fitness", "pool"])
        amenity_duration = rng.randint(45, 75)
        amenity_end = commute_home_end + amenity_duration
        events.append(
            ScheduleEvent(
                commute_home_end,
                amenity_end,
                Activity.AMENITY,
                factory.amenity_location(amenity),
                f"Visit {amenity.name}",
            )
        )
        evening_start = amenity_end
    else:
        evening_start = commute_home_end

    dinner_start = evening_start
    dinner_end = dinner_start + 60
    events.append(
        ScheduleEvent(
            dinner_start,
            dinner_end,
            Activity.EAT,
            home,
            "Dinner",
        )
    )

    leisure_end = dinner_end + rng.randint(90, 150)
    events.append(
        ScheduleEvent(
            dinner_end,
            leisure_end,
            Activity.LEISURE,
            home,
            "Evening leisure",
        )
    )

    if rng.random() < 0.35:
        amenity = factory.choose_amenity(["lounge", "workspace"])
        social_end = leisure_end + rng.randint(60, 90)
        events.append(
            ScheduleEvent(
                leisure_end,
                social_end,
                Activity.AMENITY,
                factory.amenity_location(amenity),
                f"Hang out at {amenity.name}",
            )
        )
        bedtime_start = social_end
    else:
        bedtime_start = leisure_end

    lights_out = max(bedtime_start + 30, 23 * 60 + rng.randint(0, 45))
    events.append(
        ScheduleEvent(
            bedtime_start,
            lights_out,
            Activity.AT_HOME,
            home,
            "Wind down",
        )
    )
    events.append(ScheduleEvent(lights_out, 24 * 60, Activity.SLEEP, home, "Sleep"))
    return merge_events(events)


def _build_remote_worker(factory: ResidentFactory, unit: Unit) -> List[ScheduleEvent]:
    rng = factory.rng
    home = factory._home_location(unit)
    cowork = factory.choose_amenity(["workspace"])
    events: List[ScheduleEvent] = []

    wake = rng.randint(7 * 60, 8 * 60 + 30)
    events.append(ScheduleEvent(0, wake, Activity.SLEEP, home, "Sleep"))

    breakfast_end = wake + rng.randint(45, 70)
    events.append(
        ScheduleEvent(wake, breakfast_end, Activity.AT_HOME, home, "Breakfast & prep")
    )

    cowork_end = breakfast_end + rng.randint(4 * 60, 5 * 60)
    events.append(
        ScheduleEvent(
            breakfast_end,
            cowork_end,
            Activity.WORK,
            factory.amenity_location(cowork),
            "Coworking",
        )
    )

    lunch_end = cowork_end + 60
    events.append(
        ScheduleEvent(
            cowork_end,
            lunch_end,
            Activity.EAT,
            factory._outside_location("Lunch walk"),
            "Grab lunch",
        )
    )

    focus_end = lunch_end + rng.randint(2 * 60, 3 * 60)
    events.append(ScheduleEvent(lunch_end, focus_end, Activity.WORK, home, "Remote work"))

    break_end = focus_end + rng.randint(45, 75)
    events.append(
        ScheduleEvent(
            focus_end,
            break_end,
            Activity.LEISURE,
            home,
            "Streaming break",
        )
    )

    if rng.random() < 0.5:
        amenity = factory.choose_amenity(["fitness", "pool"])
        amenity_end = break_end + rng.randint(45, 60)
        events.append(
            ScheduleEvent(
                break_end,
                amenity_end,
                Activity.AMENITY,
                factory.amenity_location(amenity),
                f"Workout at {amenity.name}",
            )
        )
        dinner_start = amenity_end
    else:
        dinner_start = break_end

    dinner_end = dinner_start + 60
    events.append(ScheduleEvent(dinner_start, dinner_end, Activity.EAT, home, "Dinner"))

    social_end = dinner_end + rng.randint(90, 150)
    events.append(
        ScheduleEvent(dinner_end, social_end, Activity.LEISURE, home, "Gaming / calls")
    )

    events.append(
        ScheduleEvent(
            social_end,
            24 * 60,
            Activity.SLEEP,
            home,
            "Sleep",
        )
    )
    return merge_events(events)


def _build_family_parent(factory: ResidentFactory, unit: Unit) -> List[ScheduleEvent]:
    rng = factory.rng
    home = factory._home_location(unit)
    events: List[ScheduleEvent] = []

    wake = rng.randint(5 * 60 + 30, 6 * 60 + 30)
    events.append(ScheduleEvent(0, wake, Activity.SLEEP, home, "Sleep"))

    prep_kids = wake + rng.randint(90, 110)
    events.append(
        ScheduleEvent(wake, prep_kids, Activity.AT_HOME, home, "Breakfast & prep kids")
    )

    school_drop_end = prep_kids + 45
    events.append(
        ScheduleEvent(
            prep_kids,
            school_drop_end,
            Activity.ERRAND,
            factory._outside_location("School drop-off"),
            "School run",
        )
    )

    mid_morning_end = school_drop_end + rng.randint(2 * 60, 3 * 60)
    events.append(
        ScheduleEvent(
            school_drop_end,
            mid_morning_end,
            Activity.WORK,
            home,
            "Remote work / chores",
        )
    )

    lunch_end = mid_morning_end + 60
    events.append(ScheduleEvent(mid_morning_end, lunch_end, Activity.EAT, home, "Lunch"))

    errands_end = lunch_end + rng.randint(90, 150)
    events.append(
        ScheduleEvent(
            lunch_end,
            errands_end,
            Activity.ERRAND,
            factory._outside_location("Errands"),
            "Errands",
        )
    )

    pickup_end = errands_end + 45
    events.append(
        ScheduleEvent(
            errands_end,
            pickup_end,
            Activity.ERRAND,
            factory._outside_location("School pickup"),
            "Pickup",
        )
    )

    play_amenity = factory.choose_amenity(["family", "lounge"])
    playtime_end = pickup_end + rng.randint(90, 120)
    events.append(
        ScheduleEvent(
            pickup_end,
            playtime_end,
            Activity.LEISURE,
            factory.amenity_location(play_amenity),
            "Playtime",
        )
    )

    dinner_end = playtime_end + 90
    events.append(ScheduleEvent(playtime_end, dinner_end, Activity.EAT, home, "Dinner"))

    wind_down = dinner_end + 60
    events.append(
        ScheduleEvent(
            dinner_end,
            wind_down,
            Activity.AT_HOME,
            home,
            "Family time",
        )
    )

    events.append(ScheduleEvent(wind_down, 24 * 60, Activity.SLEEP, home, "Sleep"))
    return merge_events(events)


def _build_grad_student(factory: ResidentFactory, unit: Unit) -> List[ScheduleEvent]:
    rng = factory.rng
    home = factory._home_location(unit)
    events: List[ScheduleEvent] = []

    sleep_in = rng.randint(7 * 60 + 30, 8 * 60 + 45)
    events.append(ScheduleEvent(0, sleep_in, Activity.SLEEP, home, "Sleep"))

    morning_class_start = sleep_in + rng.randint(45, 70)
    events.append(
        ScheduleEvent(
            sleep_in,
            morning_class_start,
            Activity.AT_HOME,
            home,
            "Prep & breakfast",
        )
    )

    class_end = morning_class_start + rng.randint(3 * 60, 4 * 60)
    events.append(
        ScheduleEvent(
            morning_class_start,
            class_end,
            Activity.WORK,
            factory._outside_location("University"),
            "Classes",
        )
    )

    lunch_end = class_end + 60
    events.append(
        ScheduleEvent(
            class_end,
            lunch_end,
            Activity.EAT,
            factory._outside_location("Campus lunch"),
            "Lunch",
        )
    )

    study_end = lunch_end + rng.randint(2 * 60, 3 * 60)
    cowork = factory.named_amenity("Coworking Lounge")
    events.append(
        ScheduleEvent(
            lunch_end,
            study_end,
            Activity.WORK,
            factory.amenity_location(cowork),
            "Study",
        )
    )

    gym_chance = rng.random()
    if gym_chance < 0.5:
        amenity = factory.choose_amenity(["fitness", "sports"])
        amenity_end = study_end + rng.randint(60, 80)
        events.append(
            ScheduleEvent(
                study_end,
                amenity_end,
                Activity.AMENITY,
                factory.amenity_location(amenity),
                f"Workout at {amenity.name}",
            )
        )
        evening_start = amenity_end
    else:
        evening_start = study_end

    social_end = evening_start + rng.randint(90, 180)
    events.append(
        ScheduleEvent(
            evening_start,
            social_end,
            Activity.LEISURE,
            factory._outside_location("Hangout"),
            "Social",
        )
    )

    events.append(
        ScheduleEvent(
            social_end,
            24 * 60,
            Activity.SLEEP,
            home,
            "Sleep",
        )
    )
    return merge_events(events)


def _build_fitness_enthusiast(factory: ResidentFactory, unit: Unit) -> List[ScheduleEvent]:
    rng = factory.rng
    home = factory._home_location(unit)
    fitness_center = factory.choose_amenity(["fitness"])
    pool = factory.choose_amenity(["pool"])
    events: List[ScheduleEvent] = []

    wake = rng.randint(5 * 60, 6 * 60)
    events.append(ScheduleEvent(0, wake, Activity.SLEEP, home, "Sleep"))

    workout_end = wake + rng.randint(75, 90)
    events.append(
        ScheduleEvent(
            wake,
            workout_end,
            Activity.AMENITY,
            factory.amenity_location(fitness_center),
            "Morning workout",
        )
    )

    recovery_end = workout_end + 45
    events.append(
        ScheduleEvent(
            workout_end,
            recovery_end,
            Activity.AMENITY,
            factory.amenity_location(pool),
            "Pool recovery",
        )
    )

    breakfast_end = recovery_end + 45
    events.append(
        ScheduleEvent(
            recovery_end,
            breakfast_end,
            Activity.EAT,
            home,
            "Breakfast",
        )
    )

    work_start = breakfast_end
    work_end = work_start + rng.randint(8 * 60, 9 * 60)
    events.append(
        ScheduleEvent(
            work_start,
            work_end,
            Activity.WORK,
            factory._work_location(unit),
            "Work",
        )
    )

    commute_home_end = work_end + 40
    events.append(
        ScheduleEvent(
            work_end,
            commute_home_end,
            Activity.COMMUTE,
            factory._outside_location("Commute"),
            "Commute",
        )
    )

    evening_session_end = commute_home_end + rng.randint(45, 60)
    events.append(
        ScheduleEvent(
            commute_home_end,
            evening_session_end,
            Activity.AMENITY,
            factory.amenity_location(fitness_center),
            "Evening training",
        )
    )

    dinner_end = evening_session_end + 75
    events.append(
        ScheduleEvent(
            evening_session_end,
            dinner_end,
            Activity.EAT,
            home,
            "Dinner",
        )
    )

    wind_down = dinner_end + 90
    events.append(
        ScheduleEvent(
            dinner_end,
            wind_down,
            Activity.LEISURE,
            home,
            "Recovery",
        )
    )

    events.append(ScheduleEvent(wind_down, 24 * 60, Activity.SLEEP, home, "Sleep"))
    return merge_events(events)


PERSONA_PROFILES: Tuple[PersonaProfile, ...] = (
    PersonaProfile(
        name="urban_professional",
        occupations=("Software Engineer", "Consultant", "Financial Analyst", "Product Manager"),
        age_range=(25, 42),
        schedule_builder=_build_urban_professional,
        amenity_preferences={"fitness": 0.7, "pool": 0.4, "lounge": 0.3},
    ),
    PersonaProfile(
        name="remote_worker",
        occupations=("UX Designer", "Writer", "Data Scientist", "Entrepreneur"),
        age_range=(24, 45),
        schedule_builder=_build_remote_worker,
        amenity_preferences={"workspace": 0.9, "fitness": 0.5, "lounge": 0.4},
    ),
    PersonaProfile(
        name="family_parent",
        occupations=("Marketing Manager", "HR Director", "Teacher", "Accountant"),
        age_range=(32, 52),
        schedule_builder=_build_family_parent,
        amenity_preferences={"spa": 0.5, "lounge": 0.6, "pool": 0.4, "family": 0.7},
    ),
    PersonaProfile(
        name="grad_student",
        occupations=("Graduate Student", "Teaching Assistant", "Research Assistant"),
        age_range=(22, 30),
        schedule_builder=_build_grad_student,
        amenity_preferences={"workspace": 0.8, "fitness": 0.3, "sports": 0.3},
    ),
    PersonaProfile(
        name="fitness_enthusiast",
        occupations=("Trainer", "Physical Therapist", "Athlete", "Wellness Coach"),
        age_range=(23, 38),
        schedule_builder=_build_fitness_enthusiast,
        amenity_preferences={"fitness": 1.0, "pool": 0.7, "spa": 0.5},
    ),
)


APPEARANCE_PALETTES: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "urban_professional": {
        "hair": ("#2f2c28", "#4a3826", "#a67b5b", "#c49a6c"),
        "outfit": ("#1f6feb", "#2563eb", "#334155"),
        "accent": ("#22d3ee", "#a855f7", "#f97316"),
    },
    "remote_worker": {
        "hair": ("#362c3a", "#5f2f45", "#b36a5e", "#d4a373"),
        "outfit": ("#14b8a6", "#0ea5e9", "#f59e0b"),
        "accent": ("#ec4899", "#60a5fa", "#facc15"),
    },
    "family_parent": {
        "hair": ("#3f2f2f", "#623412", "#b07946", "#d9b48f"),
        "outfit": ("#f97316", "#ea580c", "#ef4444"),
        "accent": ("#22c55e", "#facc15", "#c026d3"),
    },
    "grad_student": {
        "hair": ("#1f2937", "#4b5563", "#9ca3af", "#e5e7eb"),
        "outfit": ("#8b5cf6", "#3b82f6", "#14b8a6"),
        "accent": ("#f472b6", "#fb7185", "#60a5fa"),
    },
    "fitness_enthusiast": {
        "hair": ("#1f1f1f", "#3b3836", "#6b7280", "#f3f4f6"),
        "outfit": ("#22c55e", "#10b981", "#0d9488"),
        "accent": ("#facc15", "#f97316", "#ef4444"),
    },
}
