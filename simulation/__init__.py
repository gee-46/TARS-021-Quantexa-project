"""QuantumFlow Microscopic Traffic Simulation Package.

Lightweight, deterministic discrete-time 4-intersection traffic simulator
for objective comparative evaluation of traffic signal plans.
"""

from simulation.models import Vehicle, SignalState
from simulation.scenario import SimulationScenario, EmergencyVehicleConfig, create_default_simulation_scenario
from simulation.metrics import SimulationMetrics
from simulation.emergency_events import (
    IntersectionSignalMode,
    EmergencyEventType,
    EmergencyEvent,
)
from simulation.emergency_controller import EmergencyCorridorController
from simulation.engine import TrafficSimulator, simulate
from simulation.integration import (
    QuantumFlowRunResult,
    RunComparisonResult,
    run_quantumflow_demo,
    compare_runs,
    create_canonical_demo_scenario,
)

__all__ = [
    "Vehicle",
    "SignalState",
    "SimulationScenario",
    "EmergencyVehicleConfig",
    "create_default_simulation_scenario",
    "create_canonical_demo_scenario",
    "SimulationMetrics",
    "IntersectionSignalMode",
    "EmergencyEventType",
    "EmergencyEvent",
    "EmergencyCorridorController",
    "TrafficSimulator",
    "simulate",
    "QuantumFlowRunResult",
    "RunComparisonResult",
    "run_quantumflow_demo",
    "compare_runs",
]

