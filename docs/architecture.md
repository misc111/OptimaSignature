# Optima Signature Simulation Architecture

## Overview
The project models Optima Signature as a living building populated by AI-driven residents. The core goals are:
- Represent the building's physical layout, amenities, and residential units.
- Populate the building with synthetic residents that possess demographic traits, lifestyle patterns, and daily schedules.
- Advance time in discrete simulation ticks, updating each resident's activity, location, and interactions with amenities.
- Surface the evolving building state through both a command line driver and a lightweight web dashboard.

## High-Level Components

### Core Simulation Package (`optima_sim`)
- `core/entities.py`: Data models for the building, floors, units, amenities, and residents' live state.
- `core/schedule.py`: Schedule templates and generators that synthesize minute-by-minute plans for residents.
- `core/simulation.py`: Simulation engine that advances time, drives elevator logistics, animates resident movement targets, logs notable events, and aggregates statistics.
- `data/building_config.py`: Authoritative description of Optima Signature's floors, unit mix, amenity locations, and service capacities.
- `data/resident_profiles.py`: Lifestyle personas that determine how schedules and preferences are produced.

### Drivers
- `main.py`: Command line entry point that runs the simulation loop, prints summaries, and demonstrates aggregate statistics after a configurable number of days.
- `server.py`: Flask-based API that exposes a JSON snapshot of the current simulation state. The simulation runs in a background thread so clients can poll without blocking.

### Frontend (`frontend/`)
- `index.html`: Canvas-driven digital twin experience with HUD overlays and time controls.
- `app.js`: Polls the `/state` endpoint, interpolates resident movement, renders elevators, sun/moon cycle, and handles speed adjustments.
- `styles.css`: Neon-inspired styling for the dashboard and overlays.

### Testing
- `tests/test_elevator_movement.py`: Behavioural specs that validate elevator boarding, vertical confinement, arrival states, and smooth motion profiles.

### Shared Utilities
- `core/time_utils.py`: Helpers for converting between minutes, timestamps, and human-readable labels.

## Simulation Flow
1. The simulation is initialized with building metadata and a generated set of residents that fill the building's units.<br>
2. Each resident receives a probabilistic schedule built from persona-specific templates. Activities include sleep, commute, work, leisure, amenity visits, and errands.<br>
3. The engine advances time in five-minute ticks. For each tick, the current schedule segment determines the resident's location. Location transitions generate events when they involve amenities, arrivals/departures, or crowding conditions.<br>
4. Statistics such as amenity occupancy, elevator demand, and resident mood are updated per tick.

## Extensibility Notes
- Additional persona types can be introduced by extending `resident_profiles.py` with another template dictionary.
- Amenity simulations can be deepened by attaching specialized logic to an `AmenityBehavior` interface.
- External data (e.g., weather APIs, transit schedules) can be integrated by adding adapters within the `data` package and referencing them from schedule generation.

## Future Enhancements
- Persist simulation state to disk to allow pause/resume.
- Introduce AI-driven decision-making for residents (e.g., reinforcement learning for amenity usage).
- Model building services (elevators, maintenance staff) with queueing simulations.
- Expand the frontend into a richer game-like experience with interactive controls and time controls.
