"""Single registry of every scenario the dashboard and the HTTP API can run."""

from typing import Dict

from simulation import belagavi
from simulation.scenario import SimulationScenario, create_canonical_scenarios

CANONICAL_TITLES = {
    "scenario_a_balanced": "A - Balanced traffic",
    "scenario_b_congested": "B - Heavy congestion",
    "scenario_c_bus_corridor": "C - Bus / person-heavy corridor",
    "scenario_d_single_emergency": "D - Single ambulance",
    "scenario_e_two_emergency_conflict": "E - Two conflicting ambulances",
    "scenario_f_three_emergency_conflict": "F - Three conflicting emergency vehicles",
    "scenario_g_adaptive_high_demand": "G - High-demand adaptive traffic",
    "belagavi_normal": "Belagavi-inspired: normal (illustrative)",
    "belagavi_peak": "Belagavi-inspired: peak (illustrative)",
    "belagavi_peak_two_ambulances": "Belagavi-inspired: peak + two ambulances (illustrative)",
}


def all_scenarios() -> Dict[str, SimulationScenario]:
    scenarios = dict(create_canonical_scenarios())
    for kind in ("normal", "peak", "peak_two_ambulances"):
        sc = belagavi.belagavi_scenario(kind)
        scenarios[sc.scenario_id] = sc
    return scenarios


def is_belagavi_inspired(scenario_id: str) -> bool:
    return scenario_id.startswith("belagavi_")
