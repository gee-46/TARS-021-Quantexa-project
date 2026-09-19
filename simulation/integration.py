"""QuantumFlow End-to-End Integration Contract and Demo Orchestration Layer.

Provides the authoritative backend contract connecting:
1. Offline Normal Optimization (QUBO -> QAOA Primary -> Classical SA Fallback)
2. Decoded Normal Signal Timing Plan
3. Discrete-Time Microscopic Traffic Simulator
4. Dynamic Route-Aware Emergency Green Corridor Overlay
5. Quantitative Telemetry Aggregation & JSON-Safe Serialization

Boundary Guarantees:
- Pure backend execution; zero UI/frontend code.
- QAOA is an optimization component, not the real-time emergency controller.
- SA provides automated classical fallback when operationally required.
- Emergency preemption operates dynamically at runtime without mutating QUBO mathematics.
- All metrics are measured from simulation execution; no hard-coded or fabricated results.
- No claims of quantum speedup, quantum advantage, or declaring winners.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple, Optional, Any, Sequence, Union
import json
import numpy as np

from optimization.variables import INTERSECTIONS, DURATIONS, NUM_VARIABLES
from optimization.traffic_objectives import TrafficState
from optimization.emergency import EmergencyConstraints
from optimization.qubo_builder import FullQUBOConfig, build_qubo
from optimization.qubo_model import QUBOModel
from optimization.controllers import (
    BaseController,
    ControllerOutput,
    HybridController,
    SimulatedAnnealingController,
    FixedTimeController,
    RuleBasedController,
)
from simulation.models import Vehicle, SignalState
from simulation.scenario import (
    SimulationScenario,
    EmergencyVehicleConfig,
    create_default_simulation_scenario,
)
from simulation.metrics import SimulationMetrics
from simulation.emergency_events import (
    IntersectionSignalMode,
    EmergencyEventType,
    EmergencyEvent,
)
from simulation.emergency_controller import EmergencyCorridorController
from simulation.engine import TrafficSimulator


def _to_json_safe(val: Any) -> Any:
    """Recursively convert custom objects, NumPy types, and containers into JSON-safe standard Python primitives.

    Converts:
    - bool, np.bool_ -> bool
    - int, np.integer -> int
    - float, np.floating -> float
    - str -> str
    - Enum -> enum.value (sanitized)
    - dataclass / to_dict() -> dict (sanitized)
    - list, tuple, set, ndarray -> list (sanitized)
    - dict -> dict with str keys (sanitized)
    - None -> None
    """
    if val is None:
        return None
    # Boolean check must precede integer check because in Python isinstance(True, int) is True.
    if isinstance(val, (bool, np.bool_)):
        return bool(val)
    if isinstance(val, (int, np.integer)):
        return int(val)
    if isinstance(val, (float, np.floating)):
        return float(val)
    if isinstance(val, str):
        return str(val)
    if isinstance(val, np.ndarray):
        return [_to_json_safe(x) for x in val.tolist()]
    if isinstance(val, (list, tuple, set)):
        return [_to_json_safe(x) for x in val]
    if isinstance(val, dict):
        return {str(k): _to_json_safe(v) for k, v in val.items()}
    if hasattr(val, "value"):  # Enum support
        return _to_json_safe(val.value)
    if hasattr(val, "to_dict"):
        return _to_json_safe(val.to_dict())
    if hasattr(val, "__dataclass_fields__"):
        return _to_json_safe(asdict(val))
    return str(val)


@dataclass(frozen=True)
class QuantumFlowRunResult:
    """Structured, comprehensive outcome container for an end-to-end QuantumFlow execution."""

    # Identification
    run_id: str
    scenario_id: str
    seed: int

    # Normal Optimization
    normal_controller: str
    normal_signal_plan: Dict[str, int]
    optimization_status: str
    optimization_solver: str
    optimization_energy: float
    optimization_runtime: float
    optimization_fallback_used: bool
    optimization_fallback_reason: Optional[str] = None
    canonical_bitstring: Optional[str] = None
    binary_vector: Optional[List[int]] = None
    onehot_valid: bool = True
    emergency_valid: bool = True

    # Traffic Performance
    simulation_duration: int = 300
    throughput: int = 0
    average_waiting_time: float = 0.0
    max_queue: int = 0
    average_queue: float = 0.0
    vehicles_generated: int = 0
    vehicles_completed: int = 0
    normal_vehicles_waiting_time: float = 0.0

    # Emergency Corridor Telemetry
    emergency_present: bool = False
    emergency_corridor_enabled: bool = False
    emergency_detected_time: Optional[int] = None
    emergency_corridor_activated_time: Optional[int] = None
    emergency_completed_time: Optional[int] = None
    emergency_response_time: Optional[float] = None
    emergency_waiting_time: Optional[float] = None
    emergency_travel_time: Optional[float] = None
    emergency_completed: bool = False
    emergency_intersections_cleared: int = 0
    emergency_preemption_count: int = 0
    corridor_event_log: List[Dict[str, Any]] = field(default_factory=list)

    # System State
    final_signal_states: Dict[str, str] = field(default_factory=dict)
    recovery_completed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert result object into a pure JSON-serializable Python dictionary without custom encoders."""
        raw = asdict(self)
        return _to_json_safe(raw)


@dataclass(frozen=True)
class RunComparisonResult:
    """Objective arithmetic comparison record between two QuantumFlowRunResult executions (quantumflow - baseline)."""

    emergency_response_delta: Optional[float]
    emergency_wait_delta: Optional[float]
    normal_wait_delta: float
    average_wait_delta: float
    throughput_delta: int
    max_queue_delta: int
    preemption_delta: int
    energy_delta: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert comparison to a pure JSON-serializable dictionary."""
        return _to_json_safe(asdict(self))

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like indexing access to comparison deltas."""
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"RunComparisonResult has no field '{key}'.")

    def get(self, key: str, default: Any = None) -> Any:
        """Safe dictionary-like field access."""
        return getattr(self, key, default)


def compare_runs(
    baseline: QuantumFlowRunResult,
    quantumflow: QuantumFlowRunResult,
) -> RunComparisonResult:
    """Calculate objective, factual arithmetic deltas between a baseline run and a QuantumFlow run.

    Formula: delta = quantumflow - baseline.

    Args:
        baseline: Baseline run result (e.g., corridor disabled or fixed timing).
        quantumflow: Active QuantumFlow run result (e.g., corridor enabled or hybrid optimized).

    Returns:
        RunComparisonResult: Pure arithmetic differences without subjective labels.
    """
    # Emergency Response Delta
    if (
        quantumflow.emergency_response_time is not None
        and baseline.emergency_response_time is not None
    ):
        resp_delta: Optional[float] = float(
            quantumflow.emergency_response_time - baseline.emergency_response_time
        )
    else:
        resp_delta = None

    # Emergency Wait Delta
    if (
        quantumflow.emergency_waiting_time is not None
        and baseline.emergency_waiting_time is not None
    ):
        wait_delta: Optional[float] = float(
            quantumflow.emergency_waiting_time - baseline.emergency_waiting_time
        )
    else:
        wait_delta = None

    normal_wait_delta = float(
        quantumflow.normal_vehicles_waiting_time - baseline.normal_vehicles_waiting_time
    )
    avg_wait_delta = float(
        quantumflow.average_waiting_time - baseline.average_waiting_time
    )
    throughput_delta = int(quantumflow.throughput - baseline.throughput)
    max_q_delta = int(quantumflow.max_queue - baseline.max_queue)
    preempt_delta = int(
        quantumflow.emergency_preemption_count - baseline.emergency_preemption_count
    )
    energy_delta = float(
        quantumflow.optimization_energy - baseline.optimization_energy
    )

    return RunComparisonResult(
        emergency_response_delta=resp_delta,
        emergency_wait_delta=wait_delta,
        normal_wait_delta=normal_wait_delta,
        average_wait_delta=avg_wait_delta,
        throughput_delta=throughput_delta,
        max_queue_delta=max_q_delta,
        preemption_delta=preempt_delta,
        energy_delta=energy_delta,
    )


def create_canonical_demo_scenario(
    scenario_id: str = "canonical_phase15_demo",
    seed: int = 42,
) -> SimulationScenario:
    """Construct the canonical Phase 15 simulation scenario specification.

    Network Parameters:
        duration_seconds = 300
        cycle_length = 60
        intersections = ("I1", "I2", "I3", "I4")
        service_rate = 1.0
        travel_time_between_intersections = 2
        arrival_rates = {"I1": 0.35, "I2": 0.20, "I3": 0.15}
        initial_queues = {"I1": 10, "I2": 15, "I3": 8, "I4": 12}
        emergency_config: vehicle_id="EMERG_01", arrival_time=20, route=("I2", "I3", "I4")
    """
    emergency = EmergencyVehicleConfig(
        vehicle_id="EMERG_01",
        arrival_time=20,
        route=("I2", "I3", "I4"),
    )
    return SimulationScenario(
        scenario_id=scenario_id,
        duration_seconds=300,
        cycle_length=60,
        intersections=("I1", "I2", "I3", "I4"),
        service_rate=1.0,
        travel_time_between_intersections=2,
        arrival_rates={"I1": 0.35, "I2": 0.20, "I3": 0.15},
        initial_queues={"I1": 10, "I2": 15, "I3": 8, "I4": 12},
        emergency_config=emergency,
    )


def _build_benchmark_scenario_for_simulation(
    sim_scenario: SimulationScenario,
    seed: int,
) -> Any:
    """Construct an offline normal optimization BenchmarkScenario paired with the simulation state."""
    from optimization.benchmark import BenchmarkScenario

    state_dict = {}
    for inter in sim_scenario.intersections:
        q = float(sim_scenario.initial_queues.get(inter, 10))
        # Estimate density relative to nominal capacity
        d = min(0.95, max(0.20, q / 20.0))
        state_dict[inter] = {"queue": q, "density": d, "capacity": 100.0}

    traffic_state = TrafficState.from_dict(state_dict)
    edges = [
        (sim_scenario.intersections[i], sim_scenario.intersections[i + 1])
        for i in range(len(sim_scenario.intersections) - 1)
    ]
    config = FullQUBOConfig(
        onehot_penalty=100.0,
        wait_weight=2.0,
        capacity_weight=10.0,
        capacity_threshold=0.7,
        throughput_weight=1.0,
        service_rate=sim_scenario.service_rate,
        coupling_weight=5.0,
        default_capacity=100.0,
        emergency_weight=0.0,  # Normal optimizer solves standard traffic distribution
    )
    qubo_model = build_qubo(
        traffic_state=traffic_state,
        edges=edges,
        config=config,
        emergency_constraints=None,
    )
    return BenchmarkScenario(
        scenario_id=f"bench_{sim_scenario.scenario_id}",
        seed=seed,
        traffic_state=traffic_state,
        edges=edges,
        emergency_constraints=None,
        config=config,
        qubo_model=qubo_model,
        simulation_scenario=sim_scenario,
    )


def _resolve_controller(
    controller: Union[str, BaseController],
    **kwargs: Any,
) -> BaseController:
    """Instantiate or resolve controller adapter from name or instance."""
    if isinstance(controller, BaseController):
        return controller

    if not isinstance(controller, str):
        raise ValueError(
            f"Invalid controller type: {type(controller)}. Must be a controller string or BaseController instance."
        )

    name = controller.strip().lower()
    if name in ("hybrid", "hybrid_quantumflow"):
        return HybridController(
            name="hybrid_quantumflow",
            qaoa_p=kwargs.get("qaoa_p", 1),
            qaoa_maxiter=kwargs.get("qaoa_maxiter", 30),
            qaoa_shots=kwargs.get("qaoa_shots", 1024),
            qaoa_timeout_seconds=kwargs.get("qaoa_timeout_seconds", 60.0),
            sa_num_reads=kwargs.get("sa_num_reads", 100),
            sa_num_sweeps=kwargs.get("sa_num_sweeps", 1000),
            require_onehot=kwargs.get("require_onehot", True),
            require_emergency_valid=kwargs.get("require_emergency_valid", False),
        )
    elif name in ("sa", "classical_sa", "simulated_annealing"):
        return SimulatedAnnealingController(
            name="classical_sa",
            num_reads=kwargs.get("sa_num_reads", 100),
            num_sweeps=kwargs.get("sa_num_sweeps", 1000),
        )
    elif name in ("fixed", "fixed_time", "fixed_time_30s"):
        return FixedTimeController(
            name="fixed_time_30s",
            default_duration=kwargs.get("default_duration", 30),
            custom_plan=kwargs.get("custom_plan", None),
        )
    elif name in ("rule", "rule_based", "rule_based_actuated"):
        return RuleBasedController(
            name="rule_based_actuated",
            high_queue_threshold=kwargs.get("high_queue_threshold", 30.0),
            med_queue_threshold=kwargs.get("med_queue_threshold", 18.0),
            high_density_threshold=kwargs.get("high_density_threshold", 0.80),
            med_density_threshold=kwargs.get("med_density_threshold", 0.50),
            respect_emergency=kwargs.get("respect_emergency", False),
        )
    else:
        raise ValueError(
            f"Unknown or unsupported controller: '{controller}'. "
            f"Supported controllers: 'hybrid', 'sa', 'fixed', 'rule'."
        )


def run_quantumflow_demo(
    scenario: Optional[Any] = None,
    seed: int = 42,
    enable_emergency_corridor: bool = True,
    controller: Union[str, BaseController] = "hybrid",
    **kwargs: Any,
) -> QuantumFlowRunResult:
    """Execute end-to-end QuantumFlow pipeline: Normal Optimization -> Traffic Simulation -> Emergency Overlay -> Telemetry.

    Args:
        scenario: BenchmarkScenario or SimulationScenario. If None, uses canonical Phase 15 scenario.
        seed: Deterministic random seed for optimization and Poisson arrivals.
        enable_emergency_corridor: If True, activates runtime dynamic emergency green corridor preemption.
        controller: Controller selection ('hybrid', 'sa', 'fixed', 'rule' or BaseController).
        **kwargs: Optional hyperparameter overrides (e.g. qaoa_maxiter, sa_num_sweeps, prepare_lookahead_seconds).

    Returns:
        QuantumFlowRunResult: Structured, JSON-serializable execution outcome.
    """
    from optimization.benchmark import BenchmarkScenario

    # 1. Resolve Simulation and Benchmark Scenarios
    if scenario is None:
        sim_scenario = create_canonical_demo_scenario(seed=seed)
        bench_scenario = _build_benchmark_scenario_for_simulation(sim_scenario, seed=seed)
    elif isinstance(scenario, BenchmarkScenario):
        bench_scenario = scenario
        if scenario.simulation_scenario is not None:
            sim_scenario = scenario.simulation_scenario
        else:
            sim_scenario = create_canonical_demo_scenario(
                scenario_id=f"sim_{scenario.scenario_id}",
                seed=seed,
            )
    elif isinstance(scenario, SimulationScenario):
        sim_scenario = scenario
        bench_scenario = _build_benchmark_scenario_for_simulation(sim_scenario, seed=seed)
    else:
        raise ValueError(
            f"Invalid scenario type: {type(scenario)}. Expected BenchmarkScenario, SimulationScenario, or None."
        )

    # 2. Resolve Controller and Execute Offline Normal Optimization
    ctrl = _resolve_controller(controller, **kwargs)
    ctrl_output: ControllerOutput = ctrl.solve(bench_scenario, seed=seed)

    normal_plan = dict(ctrl_output.signal_plan)
    sim_scenario.validate_plan(normal_plan)

    opt_status = "success" if ctrl_output.error is None else "failed"
    opt_solver = ctrl_output.solver_used or ctrl.name
    opt_fallback_used = bool(ctrl_output.fallback_used) if ctrl_output.fallback_used is not None else False

    # 3. Execute Microscopic Traffic Simulation with Emergency Corridor Overlay
    lookahead = kwargs.get("prepare_lookahead_seconds", 3)
    simulator = TrafficSimulator(
        scenario=sim_scenario,
        enable_emergency_corridor=enable_emergency_corridor,
        prepare_lookahead_seconds=lookahead,
    )
    metrics: SimulationMetrics = simulator.simulate(
        signal_plan=normal_plan,
        seed=seed,
    )

    # 4. Extract Final Signal Modes & Determine Recovery State
    if simulator.last_emergency_controller is not None:
        final_signal_states = {
            inter: mode.value
            for inter, mode in simulator.last_emergency_controller.intersection_modes.items()
        }
    else:
        final_signal_states = {inter: "NORMAL" for inter in sim_scenario.intersections}

    emergency_present = sim_scenario.emergency_config is not None

    if not emergency_present:
        recovery_completed = True
    elif not enable_emergency_corridor:
        recovery_completed = True
    else:
        recovery_completed = bool(metrics.emergency_completed)

    # 5. Construct Final Structured Run Result
    run_id = f"run_{sim_scenario.scenario_id}_{ctrl.name}_{seed}"

    return QuantumFlowRunResult(
        run_id=run_id,
        scenario_id=sim_scenario.scenario_id,
        seed=seed,
        normal_controller=ctrl.name,
        normal_signal_plan=normal_plan,
        optimization_status=opt_status,
        optimization_solver=opt_solver,
        optimization_energy=float(ctrl_output.qubo_energy),
        optimization_runtime=float(ctrl_output.runtime_seconds),
        optimization_fallback_used=opt_fallback_used,
        optimization_fallback_reason=ctrl_output.fallback_reason,
        canonical_bitstring=ctrl_output.canonical_bitstring,
        binary_vector=[int(b) for b in ctrl_output.binary_vector] if ctrl_output.binary_vector else None,
        onehot_valid=bool(ctrl_output.onehot_valid),
        emergency_valid=bool(ctrl_output.emergency_valid),
        simulation_duration=int(sim_scenario.duration_seconds),
        throughput=int(metrics.throughput),
        average_waiting_time=float(metrics.average_waiting_time),
        max_queue=int(metrics.max_queue),
        average_queue=float(metrics.average_queue),
        vehicles_generated=int(metrics.vehicles_generated),
        vehicles_completed=int(metrics.vehicles_completed),
        normal_vehicles_waiting_time=float(metrics.normal_vehicles_waiting_time),
        emergency_present=emergency_present,
        emergency_corridor_enabled=enable_emergency_corridor,
        emergency_detected_time=metrics.emergency_detected_time,
        emergency_corridor_activated_time=metrics.emergency_corridor_activated_time,
        emergency_completed_time=metrics.emergency_completed_time,
        emergency_response_time=metrics.emergency_response_time,
        emergency_waiting_time=metrics.emergency_waiting_time,
        emergency_travel_time=metrics.emergency_travel_time,
        emergency_completed=bool(metrics.emergency_completed),
        emergency_intersections_cleared=int(metrics.emergency_intersections_cleared),
        emergency_preemption_count=int(metrics.emergency_preemption_count),
        corridor_event_log=metrics.corridor_event_log,
        final_signal_states=final_signal_states,
        recovery_completed=recovery_completed,
    )
