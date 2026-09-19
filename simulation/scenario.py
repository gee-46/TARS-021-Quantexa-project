"""Simulation Scenario Definition and Standard Configurations.

Defines network topology, simulation duration, arrival rates, initial queues,
and scheduled emergency vehicle configurations.
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, Any, Sequence, List
import numpy as np


@dataclass(frozen=True)
class EmergencyVehicleConfig:
    """Scheduled emergency vehicle parameters."""

    vehicle_id: str
    arrival_time: int
    route: Tuple[str, ...] = ("I2", "I3", "I4")


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
        emergency_config: Optional scheduled emergency vehicle configuration.
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
