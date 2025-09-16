"""Command-line driver for the Optima Signature simulation."""
from __future__ import annotations

from collections import Counter

from optima_sim import ResidentFactory, Simulation, load_building


def main() -> None:
    building = load_building()
    factory = ResidentFactory(building, seed=2024)
    residents = factory.populate_building()
    sim = Simulation(building, residents)

    ticks_per_hour = 60 // sim.tick_minutes
    total_ticks = ticks_per_hour * 24

    print(f"Populated {len(residents)} residents across {len(building.all_units())} units.")
    print("Advancing one simulated day...\n")

    hourly_breakdown: Counter[str] = Counter()
    for tick in range(total_ticks):
        sim.step()
        if (tick + 1) % ticks_per_hour == 0:
            state = sim.state_snapshot()
            hourly_breakdown.update(state["activity_breakdown"])  # type: ignore[arg-type]
            print(
                f"[{state['clock']}] Work: {state['activity_breakdown'].get('work', 0):3d} | "
                f"Amenities: {state['activity_breakdown'].get('amenity', 0):3d} | "
                f"Leisure: {state['activity_breakdown'].get('leisure', 0):3d} | "
                f"Outside: {state['activity_breakdown'].get('commute', 0) + state['activity_breakdown'].get('away', 0)}"
            )

    state = sim.state_snapshot()
    busiest = sorted(state["amenity_load"].items(), key=lambda item: item[1], reverse=True)[:3]
    print("\nTop amenities this tick:")
    for name, load in busiest:
        print(f"  - {name}: {load} people")

    print("\nRecent events:")
    for event in state["events"][-5:]:
        print(
            f"  {event['timestamp']} | {event['resident']} -> {event['description']} ({event['location']})"
        )


if __name__ == "__main__":
    main()
