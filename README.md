# Optima Signature Simulation

A simulation-driven "digital twin" of the Optima Signature residential tower in downtown Chicago. The project procedurally generates residents, gives them realistic schedules based on lifestyle personas, advances time in five-minute ticks, and exposes the evolving state through both a CLI driver and a lightweight web dashboard.

## Features
- Ten-floor tower with three identical apartments per floor for streamlined prototyping.
- Resident personas (urban professionals, remote workers, families, grad students, fitness fanatics) with probabilistic daily routines.
- Fully simulated elevator queues, boarding, and rides connecting units, amenities, and the outside world.
- Rich appearance system with persona-driven hair/outfit palettes to spot residents at a glance.
- Minute-level activity tracking with transitions logged to an event feed plus mood drift, amenity occupancy, and commuter flows.
- Flask API streaming the latest building snapshot alongside a sprite-driven dashboard showcasing animated residents, sun/moon cycle, and real-time speed controls.
- Art-deco inspired sprite manifest (`frontend/app.manifest.json`) that powers room backdrops, props, and persona-specific animations with graceful fallbacks for missing art.

## Getting Started

### Prerequisites
- Python 3.10+
- (Optional) A virtual environment is recommended.

Install Python dependencies:

```bash
pip install -r requirements.txt
```

### Command Line Simulation

Run a single simulated day and print hourly summaries:

```bash
python main.py
```

### Web Dashboard

Start the Flask server (which runs the simulation in a background thread):

```bash
python server.py
```

Then open `frontend/index.html` in your browser. The dashboard polls the `/state` endpoint and updates every second. (If you prefer to serve the static assets via Flask, point a simple static file server at the `frontend/` directory.)

### Tests

Install dev dependencies and run the movement tests with `pytest`:

```bash
pip install -r requirements.txt
pytest
```

### Art Assets

The dashboard reads `frontend/app.manifest.json` to discover sprites. Populate the referenced `assets/sprites/` folders with PNG artwork to replace the procedural placeholders. Missing files fall back to stylised stubs so you can iterate on the manifest before final art lands.

## Project Structure

- `optima_sim/` – simulation package
  - `core/` – engine primitives and loop
    - `entities.py` – domain models for units, amenities, residents
    - `schedule.py` – schedule events and helpers
    - `simulation.py` – simulation loop with state snapshots and event logging
    - `time_utils.py` – minute-to-datetime helpers
  - `data/` – static building configuration and persona definitions
    - `building_config.py` – Optima Signature floors, units, amenities
    - `resident_profiles.py` – personas and schedule generation
- `main.py` – CLI runner for a daily cycle
- `server.py` – Flask API exposing `/state`
- `frontend/` – HTML/JS dashboard assets
- `docs/architecture.md` – design overview

## Extending the Simulation
- Add new personas by appending to `PERSONA_PROFILES` and contributing a schedule builder in `resident_profiles.py`.
- Expand amenities or adjust capacities in `building_config.py`.
- Enhance `Simulation._adjust_mood` to incorporate weather or building events.
- Replace the Flask layer with websockets for true real-time streaming or hook the simulation into a richer game engine.

## License
Distributed for educational/demonstration purposes. Adapt freely for internal use.
