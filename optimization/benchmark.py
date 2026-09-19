"""Controlled Optimization Benchmark and Evaluation Framework for QuantumFlow.

Provides reproducible scenario generation, controller execution across deterministic seeds,
structured metric logging, and JSON export/loading.

Guiding Principles:
1. Identical Test Conditions: Every controller evaluated on identical traffic states and QUBO models.
2. Objective Measurement: No claims of quantum advantage or superiority.
3. Separation of Concerns: Optimization metrics recorded directly; traffic metrics marked unavailable until simulator integration.
4. Reproducibility: Seed management across trials.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Sequence, Tuple
import os
import json
import time
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
from optimization.benchmark_metrics import (
    OptimizationMetrics,
    TrafficMetrics,
    TrialResult,
    summarize_results,
)
from simulation.scenario import (
    SimulationScenario,
    create_default_simulation_scenario,
)
from simulation.engine import simulate


@dataclass(frozen=True)
class BenchmarkScenario:
    """Immutable representation of a multi-intersection traffic scenario and its QUBO model.

    Attributes:
        scenario_id: Unique scenario identifier.
        seed: Random seed used to construct the scenario.
        traffic_state: TrafficState with queue lengths, densities, and capacities.
        edges: Directed grid topology connections.
        emergency_constraints: Active emergency corridor constraints or None.
        config: FullQUBOConfig penalty and objective weighting parameters.
        qubo_model: Assembled upper-triangular QUBOModel.
        exact_optimum_x: Optional ground truth binary vector (for validation only).
        exact_optimum_energy: Optional ground truth minimum energy (for validation only).
        simulation_scenario: Optional discrete microscopic SimulationScenario.
    """

    scenario_id: str
    seed: int
    traffic_state: TrafficState
    edges: List[Tuple[str, str]]
    emergency_constraints: Optional[EmergencyConstraints]
    config: FullQUBOConfig
    qubo_model: QUBOModel
    exact_optimum_x: Optional[Tuple[int, ...]] = None
    exact_optimum_energy: Optional[float] = None
    simulation_scenario: Optional[SimulationScenario] = None


def create_deterministic_scenario(
    scenario_id: str = "phase7_deterministic",
    seed: int = 42,
    with_simulation: bool = True,
) -> BenchmarkScenario:
    """Construct the canonical deterministic Phase 7 benchmark scenario.

    Parameters:
        Queues: I1=20, I2=35, I3=15, I4=30
        Densities: I1=0.50, I2=0.90, I3=0.60, I4=0.80
        Capacities: all = 100.0
        Edges: I1 -> I2, I2 -> I3, I3 -> I4
        Emergency Corridor: I2 -> I3 -> I4, forced_duration = 45s, weight = 50.0
        Known Exact Optimum: 001001001001, Energy ~ -95.5556

    Returns:
        BenchmarkScenario: Authoritative benchmark test case.
    """
    state_dict = {
        "I1": {"queue": 20.0, "density": 0.50, "capacity": 100.0},
        "I2": {"queue": 35.0, "density": 0.90, "capacity": 100.0},
        "I3": {"queue": 15.0, "density": 0.60, "capacity": 100.0},
        "I4": {"queue": 30.0, "density": 0.80, "capacity": 100.0},
    }
    traffic_state = TrafficState.from_dict(state_dict)
    edges = [("I1", "I2"), ("I2", "I3"), ("I3", "I4")]
    emergency = EmergencyConstraints(
        route=["I2", "I3", "I4"],
        forced_duration=45,
        emergency_weight=50.0,
    )
    config = FullQUBOConfig(
        onehot_penalty=100.0,
        wait_weight=2.0,
        capacity_weight=10.0,
        capacity_threshold=0.7,
        throughput_weight=1.0,
        service_rate=1.0,
        coupling_weight=5.0,
        default_capacity=100.0,
        emergency_weight=50.0,
    )
    qubo_model = build_qubo(
        traffic_state=traffic_state,
        edges=edges,
        config=config,
        emergency_constraints=emergency,
    )

    exact_x = (0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1)
    exact_e = float(qubo_model.energy(exact_x, include_offset=True))

    sim_scenario = None
    if with_simulation:
        sim_scenario = create_default_simulation_scenario(
            scenario_id=f"sim_{scenario_id}",
            duration_seconds=300,
            with_emergency=True,
        )

    return BenchmarkScenario(
        scenario_id=scenario_id,
        seed=seed,
        traffic_state=traffic_state,
        edges=edges,
        emergency_constraints=emergency,
        config=config,
        qubo_model=qubo_model,
        exact_optimum_x=exact_x,
        exact_optimum_energy=exact_e,
        simulation_scenario=sim_scenario,
    )


def create_random_scenario(
    scenario_id: str,
    seed: int,
    with_emergency: bool = True,
    with_simulation: bool = False,
) -> BenchmarkScenario:
    """Generate a reproducible synthetic traffic scenario with parameterized random demand.

    Args:
        scenario_id: Scenario identifier string.
        seed: Random seed controlling demand generation.
        with_emergency: If True, attaches a 2-intersection emergency corridor.
        with_simulation: If True, attaches a default SimulationScenario.

    Returns:
        BenchmarkScenario: Constructed randomized scenario.
    """
    rng = np.random.RandomState(seed)
    state_dict = {}
    for inter in INTERSECTIONS:
        q = float(rng.uniform(10.0, 45.0))
        d = float(rng.uniform(0.3, 0.95))
        state_dict[inter] = {"queue": q, "density": d, "capacity": 100.0}

    traffic_state = TrafficState.from_dict(state_dict)
    edges = [("I1", "I2"), ("I2", "I3"), ("I3", "I4")]

    emergency = None
    if with_emergency:
        emergency = EmergencyConstraints(
            route=["I2", "I3"],
            forced_duration=45,
            emergency_weight=50.0,
        )

    config = FullQUBOConfig(
        onehot_penalty=100.0,
        wait_weight=2.0,
        capacity_weight=10.0,
        capacity_threshold=0.7,
        throughput_weight=1.0,
        service_rate=1.0,
        coupling_weight=5.0,
        default_capacity=100.0,
        emergency_weight=50.0 if with_emergency else 0.0,
    )

    qubo_model = build_qubo(
        traffic_state=traffic_state,
        edges=edges,
        config=config,
        emergency_constraints=emergency,
    )

    sim_scenario = None
    if with_simulation:
        sim_scenario = create_default_simulation_scenario(
            scenario_id=f"sim_{scenario_id}",
            duration_seconds=300,
            with_emergency=with_emergency,
        )

    return BenchmarkScenario(
        scenario_id=scenario_id,
        seed=seed,
        traffic_state=traffic_state,
        edges=edges,
        emergency_constraints=emergency,
        config=config,
        qubo_model=qubo_model,
        exact_optimum_x=None,
        exact_optimum_energy=None,
        simulation_scenario=sim_scenario,
    )


def run_benchmark(
    scenarios: Sequence[BenchmarkScenario],
    controllers: Sequence[BaseController],
    num_trials: int = 5,
    base_seed: int = 42,
) -> List[TrialResult]:
    """Execute a controlled benchmark across scenarios, controllers, and trials.

    Args:
        scenarios: List of BenchmarkScenario instances.
        controllers: List of BaseController instances to evaluate.
        num_trials: Number of trials per scenario-controller pair (default 5).
        base_seed: Base seed for trial seed generation (default 42).

    Returns:
        List[TrialResult]: Complete sequence of recorded trial execution results.
    """
    results: List[TrialResult] = []

    for scenario in scenarios:
        for ctrl in controllers:
            for trial_idx in range(num_trials):
                trial_seed = base_seed + trial_idx * 1000 + scenario.seed

                # 1. Execute controller optimization
                output: ControllerOutput = ctrl.solve(scenario, seed=trial_seed)

                # 2. Compute optimality gap if exact optimum is available
                gap = None
                optimum_found = None
                if scenario.exact_optimum_energy is not None and np.isfinite(output.qubo_energy):
                    gap = float(output.qubo_energy - scenario.exact_optimum_energy)
                    if scenario.exact_optimum_x is not None:
                        exact_str = "".join(str(b) for b in scenario.exact_optimum_x)
                        optimum_found = output.canonical_bitstring == exact_str
                    else:
                        optimum_found = np.isclose(output.qubo_energy, scenario.exact_optimum_energy)

                status = "success" if output.error is None else "failed"

                opt_metrics = OptimizationMetrics(
                    status=status,
                    runtime_seconds=output.runtime_seconds,
                    qubo_energy=output.qubo_energy,
                    best_bitstring=output.canonical_bitstring,
                    fallback_used=output.fallback_used,
                    fallback_reason=output.fallback_reason,
                    solver_used=output.solver_used,
                    onehot_valid=output.onehot_valid,
                    emergency_valid=output.emergency_valid,
                    exact_optimum_energy=scenario.exact_optimum_energy,
                    optimality_gap=gap,
                    exact_optimum_found=optimum_found,
                )

                # 3. Microscopic Traffic Simulation (when SimulationScenario is configured)
                traffic_metrics = TrafficMetrics(available=False)
                if (
                    scenario.simulation_scenario is not None
                    and output.signal_plan
                    and output.onehot_valid
                ):
                    sim_metrics = simulate(
                        scenario=scenario.simulation_scenario,
                        signal_plan=output.signal_plan,
                        seed=trial_seed,
                    )
                    traffic_metrics = sim_metrics.to_traffic_metrics()

                trial_record = TrialResult(
                    scenario_id=scenario.scenario_id,
                    trial_index=trial_idx,
                    seed=trial_seed,
                    controller_name=ctrl.name,
                    signal_plan=output.signal_plan,
                    optimization_metrics=opt_metrics,
                    traffic_metrics=traffic_metrics,
                )
                results.append(trial_record)

    return results


def save_results_json(results: Sequence[TrialResult], file_path: str) -> None:
    """Save benchmark trial results to a JSON file.

    Args:
        results: Sequence of TrialResult records.
        file_path: Destination file path.
    """
    os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
    serialized = [r.to_dict() for r in results]
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(serialized, f, indent=2)


def load_results_json(file_path: str) -> List[TrialResult]:
    """Load benchmark trial results from a JSON file.

    Args:
        file_path: Source file path.

    Returns:
        List[TrialResult]: Reconstructed trial result objects.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [TrialResult.from_dict(item) for item in data]


def format_comparison_table(results: Sequence[TrialResult]) -> str:
    """Format a textual comparison table of benchmark results without rankings or winners.

    Args:
        results: Sequence of TrialResult records.

    Returns:
        str: Formatted tabular summary string.
    """
    has_traffic = any(r.traffic_metrics.available for r in results)

    if has_traffic:
        header = (
            f"{'Scenario':<22} | {'Controller':<20} | {'Trial':<5} | {'Seed':<6} | {'QUBO Energy':<12} | "
            f"{'Runtime(s)':<10} | {'Throughput':<10} | {'Avg Wait(s)':<11} | {'Max Queue':<9} | {'Emerg Resp(s)':<13}"
        )
        sep = "-" * 145
        lines = [header, sep]
        for r in results:
            om = r.optimization_metrics
            tm = r.traffic_metrics
            th_str = f"{int(tm.throughput):<10}" if tm.available and tm.throughput is not None else "N/A       "
            aw_str = f"{tm.average_waiting_time:<11.2f}" if tm.available and tm.average_waiting_time is not None else "N/A        "
            mq_str = f"{int(tm.max_queue):<9}" if tm.available and tm.max_queue is not None else "N/A      "
            er_str = f"{tm.emergency_response_time:<13.1f}" if tm.available and tm.emergency_response_time is not None else "N/A          "

            lines.append(
                f"{r.scenario_id:<22} | {r.controller_name:<20} | {r.trial_index:<5} | {r.seed:<6} | {om.qubo_energy:+12.4f} | "
                f"{om.runtime_seconds:<10.4f} | {th_str} | {aw_str} | {mq_str} | {er_str}"
            )
    else:
        header = (
            f"{'Scenario':<22} | {'Controller':<20} | {'Trial':<5} | {'Seed':<6} | {'Solver':<6} | {'Fallback':<8} | "
            f"{'QUBO Energy':<12} | {'Gap':<10} | {'Runtime(s)':<10} | {'1-Hot':<5} | {'Emerg':<5}"
        )
        sep = "-" * 135
        lines = [header, sep]
        for r in results:
            om = r.optimization_metrics
            gap_str = f"{om.optimality_gap:+9.4f}" if om.optimality_gap is not None else "   N/A    "
            fb_str = str(om.fallback_used) if om.fallback_used is not None else "False"
            solver_str = om.solver_used if om.solver_used else "N/A"
            lines.append(
                f"{r.scenario_id:<22} | {r.controller_name:<20} | {r.trial_index:<5} | {r.seed:<6} | {solver_str:<6} | {fb_str:<8} | "
                f"{om.qubo_energy:+12.4f} | {gap_str:<10} | {om.runtime_seconds:<10.4f} | {str(om.onehot_valid):<5} | {str(om.emergency_valid):<5}"
            )

    return "\n".join(lines)
