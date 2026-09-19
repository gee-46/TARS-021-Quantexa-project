"""Belagavi digital-twin *abstraction* of the QuantumFlow arterial.

IMPORTANT - what this is and is not
-----------------------------------
This maps the four abstract simulator nodes (I1..I4) onto recognisable Belagavi junction
*labels* so a demo reads as a place instead of "I1 -> I2 -> I3 -> I4". It is a schematic:

* Junction names are illustrative labels chosen for presentation.
* The order of junctions, distances, signal timings and traffic volumes are NOT measured
  from Belagavi. Arrival rates are invented "plausible peak" numbers.
* Nothing here validates the simulator against real traffic, and no result should be
  presented as a prediction for the real city.

To calibrate the twin, replace ``BELAGAVI_JUNCTIONS`` (and fill ``lat``/``lon``) with surveyed
data and replace the demand numbers in ``belagavi_scenario`` with counted flows.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from simulation.models import VehicleTypeConfig
from simulation.scenario import EmergencyVehicleConfig, SimulationScenario

DISCLAIMER = (
    "Simulation abstraction, not a validated model of Belagavi. Junction names are illustrative labels; "
    "layout, distances, signal timings and traffic volumes are assumed, not measured."
)


@dataclass(frozen=True)
class Junction:
    node_id: str  # simulator node (I1..I4)
    name: str  # display label
    role: str  # what the node stands for in the story
    lat: Optional[float] = None  # fill in from a survey to calibrate
    lon: Optional[float] = None


BELAGAVI_JUNCTIONS: Tuple[Junction, ...] = (
    Junction("I1", "Central Bus Stand", "transit hub (bus-heavy entry)"),
    Junction("I2", "Chennamma Circle", "city-centre circle"),
    Junction("I3", "RPD Cross", "contested junction (both ambulance routes)"),
    Junction("I4", "Tilakwadi", "eastern entry toward hospital belt"),
)

_NAMES: Dict[str, str] = {j.node_id: j.name for j in BELAGAVI_JUNCTIONS}


def junction_name(node_id: str) -> str:
    """Display label for a simulator node ('I3' -> 'RPD Cross')."""
    return _NAMES.get(node_id, node_id)


def label_route(route: Tuple[str, ...]) -> str:
    return " -> ".join(junction_name(n) for n in route)


def belagavi_scenario(kind: str = "peak_two_ambulances", duration_seconds: int = 300) -> SimulationScenario:
    """Ready-made demo scenarios on the Belagavi abstraction.

    kinds: 'normal', 'peak', 'peak_two_ambulances'. Demand values are assumptions (see module doc).
    """
    common = dict(
        duration_seconds=duration_seconds,
        vehicle_type_config=VehicleTypeConfig(car_occupancy=1.8, bus_occupancy=40.0),
        bus_probabilities={"I1": 0.30, "I2": 0.10},
        cross_street_rates={"I1": 0.20, "I2": 0.25, "I3": 0.25, "I4": 0.15},
    )
    if kind == "normal":
        return SimulationScenario(
            scenario_id="belagavi_normal",
            arrival_rates={"I1": 0.25, "I2": 0.25, "I3": 0.20, "I4": 0.20},
            initial_queues={"I1": 6, "I2": 8, "I3": 6, "I4": 5},
            **common,
        )
    if kind == "peak":
        return SimulationScenario(
            scenario_id="belagavi_peak",
            arrival_rates={"I1": 0.50, "I2": 0.45, "I3": 0.40, "I4": 0.30},
            initial_queues={"I1": 20, "I2": 24, "I3": 18, "I4": 14},
            **common,
        )
    if kind == "peak_two_ambulances":
        return SimulationScenario(
            scenario_id="belagavi_peak_two_ambulances",
            arrival_rates={"I1": 0.50, "I2": 0.45, "I3": 0.40, "I4": 0.30},
            initial_queues={"I1": 20, "I2": 24, "I3": 18, "I4": 14},
            emergency_vehicles=(
                EmergencyVehicleConfig("AMB_A", arrival_time=15, route=("I1", "I2", "I3"), priority=1),
                EmergencyVehicleConfig("AMB_B", arrival_time=18, route=("I4", "I3", "I2"), priority=2),
            ),
            **common,
        )
    raise ValueError(f"Unknown Belagavi scenario '{kind}'. Use 'normal', 'peak' or 'peak_two_ambulances'.")


def describe() -> Dict[str, object]:
    """Network description for the dashboard (schematic layout only)."""
    return {
        "disclaimer": DISCLAIMER,
        "junctions": [
            {"node_id": j.node_id, "name": j.name, "role": j.role, "lat": j.lat, "lon": j.lon}
            for j in BELAGAVI_JUNCTIONS
        ],
        "corridor_order": [j.node_id for j in BELAGAVI_JUNCTIONS],
    }
