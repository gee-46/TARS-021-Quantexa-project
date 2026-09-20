"""Belagavi-inspired corridor for the QuantumFlow arterial (NOT a digital twin).

What is real and what is assumed
--------------------------------
* REAL: the four junction locations and the road geometry between them come from OpenStreetMap
  (see ``simulation/data/belagavi_geo.json``, produced by ``examples/fetch_belagavi_geo.py``).
* ASSUMED: which junctions form "the corridor", the signal timings, demand and every traffic volume.
  Nothing here validates the simulator against real Belagavi traffic, and no result should be
  presented as a prediction for the real city.
* 'Tilakwadi' is the centroid of the suburb, not a single junction.
"""

from dataclasses import dataclass
import json
import os
from typing import Any, Dict, Optional, Tuple

from simulation.models import VehicleTypeConfig
from simulation.scenario import EmergencyVehicleConfig, SimulationScenario

DISCLAIMER = (
    "Belagavi-inspired corridor - not a digital twin and not a validated model of Belagavi. Junction locations are real "
    "OpenStreetMap places, but which junctions form the corridor, signal timings and traffic volumes are assumed, not measured."
)


GEO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "belagavi_geo.json")


def load_geo() -> Dict[str, Any]:
    """Real OpenStreetMap locations + road geometry (fetched once by examples/fetch_belagavi_geo.py)."""
    with open(GEO_PATH, encoding="utf-8") as f:
        return json.load(f)


@dataclass(frozen=True)
class Junction:
    node_id: str  # simulator node (I1..I4)
    name: str  # real place name (OpenStreetMap)
    role: str  # what the node stands for in the story
    lat: Optional[float] = None
    lon: Optional[float] = None
    osm: Optional[str] = None  # OpenStreetMap object, e.g. "way/321455352"


_ROLES = {
    "I1": "transit hub (KSRTC bus station, bus-heavy entry)",
    "I2": "city-centre roundabout",
    "I3": "central junction (both ambulance routes cross here)",
    "I4": "southern suburb, toward the hospital belt",
}


def _build_junctions() -> Tuple[Junction, ...]:
    return tuple(
        Junction(j["node_id"], j["name"], _ROLES.get(j["node_id"], ""), j["lat"], j["lon"], j["osm"])
        for j in load_geo()["junctions"]
    )


BELAGAVI_JUNCTIONS: Tuple[Junction, ...] = _build_junctions()

_NAMES: Dict[str, str] = {j.node_id: j.name for j in BELAGAVI_JUNCTIONS}


def junction_name(node_id: str) -> str:
    """Display label for a simulator node ('I3' -> 'Tilak Chowk')."""
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
    """Network description for the dashboard: real OpenStreetMap junction locations, assumed traffic."""
    return {
        "disclaimer": DISCLAIMER,
        "junctions": [
            {"node_id": j.node_id, "name": j.name, "role": j.role, "lat": j.lat, "lon": j.lon, "osm": j.osm}
            for j in BELAGAVI_JUNCTIONS
        ],
        "corridor_order": [j.node_id for j in BELAGAVI_JUNCTIONS],
    }
