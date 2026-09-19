"""Simulation Scenario Definition and Standard Configurations.

Defines network topology, simulation duration, arrival rates, initial queues,
and scheduled emergency vehicle configurations.
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, Any, Sequence, List
import numpy as np

from simulation.models import VehicleTypeConfig


@dataclass(frozen=True)
class EmergencyVehicleConfig:
    """Scheduled emergency vehicle parameters."""

    vehicle_id: str
    arrival_time: int
    route: Tuple[str, ...] = ("I2", "I3", "I4")
    priority: int = 1


@dataclass(frozen=True)
class SimulationScenario:
    """Complete parameter specification for a discrete traffic simulation run.

    Attributes:
        scenario_id: Unique scenario identifier.
        duration_seconds: Total simulation time horizon in seconds (default 300).
        cycle_length: Signal cycle length in seconds (default 60).
        intersections: Sequence of network intersections in order (default I1..I4).
        service_rate: Maximum vehicles served per green second per intersection (default 1.0).
        travel_time_between_intersections: Seconds for vehicle to transit between adjacent intersections (default 2).
        arrival_rates: Vehicles per second arriving at network entry points (e.g. {"I1": 0.35, ...}).
        initial_queues: Number of vehicles already waiting in queue at t=0.
        emergency_config: Optional primary scheduled emergency vehicle configuration (backward compatible).
        emergency_vehicles: Sequence of 1 or more scheduled emergency vehicles for multi-emergency simulation.
        vehicle_type_config: Configurable occupancy for cars, buses, etc.
        bus_probabilities: Probability of bus arrivals per intersection (e.g. {"I1": 0.1}).
        cross_street_rates: Optional cross-street arrivals per second per intersection. Cross traffic is only
            served while the main arterial is NOT green, so preempting the arterial for an ambulance costs
            cross-street civilians real delay. Empty (default) disables cross traffic.
    """

    scenario_id: str
    duration_seconds: int = 300
    cycle_length: int = 60
    intersections: Tuple[str, ...] = ("I1", "I2", "I3", "I4")
    service_rate: float = 1.0
    travel_time_between_intersections: int = 2
    arrival_rates: Dict[str, float] = field(default_factory=lambda: {"I1": 0.30, "I2": 0.15, "I3": 0.10})
    initial_queues: Dict[str, int] = field(default_factory=lambda: {"I1": 5, "I2": 8, "I3": 4, "I4": 6})
    emergency_config: Optional[EmergencyVehicleConfig] = None
    emergency_vehicles: Tuple[EmergencyVehicleConfig, ...] = ()
    vehicle_type_config: VehicleTypeConfig = field(default_factory=VehicleTypeConfig)
    bus_probabilities: Dict[str, float] = field(default_factory=dict)
    cross_street_rates: Dict[str, float] = field(default_factory=dict)

    def get_all_emergency_configs(self) -> Tuple[EmergencyVehicleConfig, ...]:
        """Return combined tuple of all configured emergency vehicles."""
        configs = list(self.emergency_vehicles)
        if self.emergency_config is not None and self.emergency_config not in configs:
            configs.insert(0, self.emergency_config)
        return tuple(configs)

    def validate_plan(self, signal_plan: Dict[str, int]) -> None:
        """Validate that signal plan covers all network intersections with allowed durations."""
        valid_durations = {15, 30, 45}
        for inter in self.intersections:
            if inter not in signal_plan:
                raise ValueError(f"Signal plan missing duration for intersection '{inter}'.")
            dur = signal_plan[inter]
            if dur not in valid_durations:
                raise ValueError(
                    f"Invalid duration {dur}s for intersection '{inter}'. Must be in {valid_durations}."
                )


def create_default_simulation_scenario(
    scenario_id: str = "default_4_intersection",
    duration_seconds: int = 300,
    cycle_length: int = 60,
    with_emergency: bool = True,
) -> SimulationScenario:
    """Construct a standard 4-intersection simulation scenario matching the Phase 7 network."""
    emergency = None
    if with_emergency:
        emergency = EmergencyVehicleConfig(
            vehicle_id="EMERG_01",
            arrival_time=15,
            route=("I2", "I3", "I4"),
        )

    return SimulationScenario(
        scenario_id=scenario_id,
        duration_seconds=duration_seconds,
        cycle_length=cycle_length,
        intersections=("I1", "I2", "I3", "I4"),
        service_rate=1.0,
        travel_time_between_intersections=2,
        arrival_rates={"I1": 0.35, "I2": 0.20, "I3": 0.15},
        initial_queues={"I1": 10, "I2": 15, "I3": 8, "I4": 12},
        emergency_config=emergency,
    )


def create_canonical_scenarios(duration_seconds: int = 300) -> Dict[str, SimulationScenario]:
    """Construct the full suite of canonical benchmark evaluation scenarios (A through G).

    Scenarios:
        - Scenario A: Normal balanced traffic
        - Scenario B: Heavy congestion
        - Scenario C: Bus/person-heavy transit corridor
        - Scenario D: Single emergency vehicle
        - Scenario E: Two conflicting emergency vehicles (opposing routes at I3)
        - Scenario F: Three simultaneous emergency vehicles contending for junction
        - Scenario G: High-demand adaptive rolling horizon traffic

    Returns:
        Dict[str, SimulationScenario]: Mapped scenario suite keyed by identifier.
    """
    scenarios: Dict[str, SimulationScenario] = {}

    # Scenario A: Normal balanced traffic
    scenarios["scenario_a_balanced"] = SimulationScenario(
        scenario_id="scenario_a_balanced",
        duration_seconds=duration_seconds,
        arrival_rates={"I1": 0.25, "I2": 0.25, "I3": 0.25, "I4": 0.25},
        initial_queues={"I1": 6, "I2": 6, "I3": 6, "I4": 6},
    )

    # Scenario B: Heavy congestion
    scenarios["scenario_b_congested"] = SimulationScenario(
        scenario_id="scenario_b_congested",
        duration_seconds=duration_seconds,
        arrival_rates={"I1": 0.60, "I2": 0.55, "I3": 0.50, "I4": 0.45},
        initial_queues={"I1": 25, "I2": 30, "I3": 20, "I4": 25},
    )

    # Scenario C: Bus/person-heavy corridor
    scenarios["scenario_c_bus_corridor"] = SimulationScenario(
        scenario_id="scenario_c_bus_corridor",
        duration_seconds=duration_seconds,
        arrival_rates={"I1": 0.35, "I2": 0.25, "I3": 0.20, "I4": 0.20},
        initial_queues={"I1": 8, "I2": 10, "I3": 8, "I4": 10},
        bus_probabilities={"I1": 0.4, "I2": 0.2},
        vehicle_type_config=VehicleTypeConfig(bus_occupancy=35.0, car_occupancy=1.5),
    )

    # Scenario D: Single emergency vehicle
    scenarios["scenario_d_single_emergency"] = SimulationScenario(
        scenario_id="scenario_d_single_emergency",
        duration_seconds=duration_seconds,
        arrival_rates={"I1": 0.30, "I2": 0.20, "I3": 0.15, "I4": 0.15},
        initial_queues={"I1": 8, "I2": 10, "I3": 8, "I4": 8},
        emergency_config=EmergencyVehicleConfig(
            vehicle_id="AMB_01",
            arrival_time=20,
            route=("I1", "I2", "I3", "I4"),
        ),
    )

    # Scenario E: Two conflicting emergencies
    scenarios["scenario_e_two_emergency_conflict"] = SimulationScenario(
        scenario_id="scenario_e_two_emergency_conflict",
        duration_seconds=duration_seconds,
        arrival_rates={"I1": 0.30, "I2": 0.20, "I3": 0.20, "I4": 0.20},
        initial_queues={"I1": 8, "I2": 12, "I3": 10, "I4": 8},
        emergency_vehicles=(
            EmergencyVehicleConfig(vehicle_id="AMB_EAST", arrival_time=15, route=("I1", "I2", "I3"), priority=1),
            EmergencyVehicleConfig(vehicle_id="AMB_WEST", arrival_time=18, route=("I4", "I3", "I2"), priority=2),
        ),
    )

    # Scenario F: Three emergency conflict
    scenarios["scenario_f_three_emergency_conflict"] = SimulationScenario(
        scenario_id="scenario_f_three_emergency_conflict",
        duration_seconds=duration_seconds,
        arrival_rates={"I1": 0.35, "I2": 0.25, "I3": 0.25, "I4": 0.20},
        initial_queues={"I1": 10, "I2": 15, "I3": 12, "I4": 10},
        emergency_vehicles=(
            EmergencyVehicleConfig(vehicle_id="AMB_1", arrival_time=10, route=("I1", "I2", "I3"), priority=1),
            EmergencyVehicleConfig(vehicle_id="AMB_2", arrival_time=12, route=("I4", "I3", "I2"), priority=2),
            EmergencyVehicleConfig(vehicle_id="FIRE_3", arrival_time=15, route=("I2", "I3", "I4"), priority=3),
        ),
    )

    # Scenario G: High-demand adaptive traffic
    scenarios["scenario_g_adaptive_high_demand"] = SimulationScenario(
        scenario_id="scenario_g_adaptive_high_demand",
        duration_seconds=duration_seconds,
        arrival_rates={"I1": 0.45, "I2": 0.40, "I3": 0.35, "I4": 0.30},
        initial_queues={"I1": 15, "I2": 20, "I3": 12, "I4": 18},
    )

    return scenarios
