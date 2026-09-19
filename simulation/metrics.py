"""Simulation Metric Definitions and Reporting Structures.

Provides quantitative traffic outcome records calculated directly from microscopic vehicle trajectories:
- total_waiting_time: Cumulative seconds spent stationary in queues.
- average_waiting_time: total_waiting_time / vehicles_generated.
- max_queue: Peak queue length across all intersections.
- average_queue: Mean queue length across all intersections over time.
- throughput: Total vehicles reaching destination and exiting the network.
- emergency_response_time: Travel seconds from entry to completion for emergency vehicle.
- person_delay: Total person-seconds of waiting delay across all vehicle passengers.
- jain_fairness_index: Mathematical fairness across approach wait distributions.
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional, List


@dataclass(frozen=True)
class SimulationMetrics:
    """Quantitative traffic outcome results produced by microscopic simulation."""

    total_waiting_time: float
    average_waiting_time: float
    max_queue: int
    average_queue: float
    throughput: int
    vehicles_generated: int
    vehicles_completed: int
    emergency_waiting_time: Optional[float] = None
    emergency_travel_time: Optional[float] = None
    emergency_completed: bool = False
    emergency_response_time: Optional[float] = None
    emergency_detected_time: Optional[int] = None
    emergency_corridor_activated_time: Optional[int] = None
    emergency_completed_time: Optional[int] = None
    emergency_intersections_cleared: int = 0
    emergency_preemption_count: int = 0
    corridor_event_log: List[Dict[str, Any]] = field(default_factory=list)
    normal_vehicles_waiting_time: float = 0.0
    emergency_corridor_enabled: bool = False
    simulation_duration: int = 300
    seed: Optional[int] = None
    total_person_delay: float = 0.0
    average_person_delay: float = 0.0
    total_passengers_served: int = 0
    jain_fairness_index: float = 1.0
    max_approach_wait: float = 0.0
    starvation_violations: int = 0
    idle_vehicle_seconds: float = 0.0
    estimated_fuel_liters: float = 0.0
    estimated_co2_kg: float = 0.0
    active_emergencies_count: int = 0
    resolved_emergency_conflicts: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_traffic_metrics(self):
        """Convert simulation metrics into a standardized TrafficMetrics container for benchmarking."""
        from optimization.benchmark_metrics import TrafficMetrics

        return TrafficMetrics(
            available=True,
            total_waiting_time=self.total_waiting_time,
            average_waiting_time=self.average_waiting_time,
            max_queue=float(self.max_queue),
            average_queue=self.average_queue,
            throughput=float(self.throughput),
            emergency_response_time=self.emergency_response_time,
            emergency_delay=self.emergency_waiting_time,
            person_delay=self.total_person_delay,
            jain_fairness_index=self.jain_fairness_index,
            max_approach_wait=self.max_approach_wait,
            starvation_violations=float(self.starvation_violations),
            idle_vehicle_seconds=self.idle_vehicle_seconds,
            estimated_fuel_liters=self.estimated_fuel_liters,
            estimated_co2_kg=self.estimated_co2_kg,
        )
