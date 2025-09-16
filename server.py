"""Flask server exposing the simulation state for a lightweight dashboard."""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Final

from flask import Flask, jsonify, request, send_from_directory

from optima_sim import ResidentFactory, Simulation, load_building

SPEED_INTERVALS: Final[dict[str, float]] = {
    "slow": 1.2,
    "normal": 0.6,
    "fast": 0.18,
}
current_speed = "normal"


FRONTEND_DIR = Path(__file__).parent / "frontend"
ASSET_DIR = Path(__file__).parent / "assets"

building = load_building()
factory = ResidentFactory(building, seed=1337)
residents = factory.populate_building()
simulation = Simulation(building, residents)
sim_lock = threading.Lock()


def _current_interval() -> float:
    return SPEED_INTERVALS.get(current_speed, SPEED_INTERVALS["normal"])

app = Flask(__name__)


def _run_simulation() -> None:
    while True:
        with sim_lock:
            simulation.step()
        time.sleep(_current_interval())


@app.route("/state", methods=["GET"])
def get_state() -> object:
    with sim_lock:
        state = simulation.state_snapshot()
        state["speed"] = current_speed
        return jsonify(state)


@app.route("/")
def index() -> object:
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def assets(path: str) -> object:
    frontend_candidate = FRONTEND_DIR / path
    if frontend_candidate.exists():
        return send_from_directory(FRONTEND_DIR, path)
    asset_candidate = ASSET_DIR / path
    if asset_candidate.exists():
        return send_from_directory(ASSET_DIR, path)
    return ("Not found", 404)


@app.post("/speed")
def set_speed() -> object:
    global current_speed
    payload = request.get_json(silent=True) or {}
    desired = payload.get("speed")
    if desired not in SPEED_INTERVALS:
        return jsonify({"error": "invalid speed"}), 400
    current_speed = desired
    return jsonify({"speed": current_speed})


if __name__ == "__main__":
    threading.Thread(target=_run_simulation, daemon=True).start()
    app.run(debug=True)
