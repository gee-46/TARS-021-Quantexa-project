"""Closed-Loop Adaptive Rolling-Horizon Signal Controller for QuantumFlow.

Transforms static one-shot signal optimization into a continuous rolling-horizon
control loop that periodically observes live simulation queues at cycle boundaries
(e.g. t = 0, 60, 120, 180, 240...), reconstructs the authoritative 12-variable QUBO,
solves with the existing Hybrid QAOA -> SA pipeline, and applies the new signal plan
safely at the beginning of each signal cycle.
"""

from dataclasses import dataclass, asdict, field
from typing import Dict, List, Tuple, Optional, Any, Sequence, Union
import time
import numpy as np

from optimization.variables import INTERSECTIONS, DURATIONS, NUM_VARIABLES
from optimization.traffic_objectives import TrafficState, TrafficObjectiveConfig
from optimization.qubo_builder import CROSS_STREET_WEIGHT, FullQUBOConfig, build_qubo
from optimization.qubo_model import QUBOModel
from optimization.decoder import decode_solution, is_valid_onehot, is_valid_emergency
from optimization.hybrid_solver import solve_hybrid, HybridSolveResult
from simulation.scenario import SimulationScenario


@dataclass(frozen=True)
class ReplanningEvent:
    """Structured telemetry record for a single rolling-horizon replanning event.

    Attributes:
        replan_index: Sequential index (0 for initial at t=0, 1, 2, ... for scheduled replans).
        simulation_time: Simulation second t when the replan was evaluated.
        trigger: 'initial' for t=0 setup, 'scheduled' for periodic cycle-boundary replans.
        queue_state: Observed queue counts per intersection at this exact boundary.
        density_state: Derived density estimates per intersection.
        signal_plan: Newly selected normal green durations {"I1": 45, ...}.
        solver_used: Optimization solver that produced the accepted plan ('qaoa' or 'sa').
        optimization_energy: Exact QUBO energy of the accepted decision vector.
        optimization_runtime: Wall-clock seconds spent solving this replan.
        fallback_used: True if classical simulated annealing fallback was invoked.
        fallback_reason: Explanation if fallback occurred (or None).
        applied: True if the plan was successfully installed into the simulator.
        canonical_bitstring: Standard 12-bit binary decision string (x_0...x_11).
        qubit_count: Model qubit count (12).
        qaoa_p: QAOA circuit depth used.
        qaoa_shots: Measurement shot count used.
        onehot_valid: True if candidate satisfies one duration per intersection.
        emergency_valid: True if candidate satisfies emergency constraints.
    """

    replan_index: int
    simulation_time: int
    trigger: str
    queue_state: Dict[str, float]
    density_state: Dict[str, float]
    signal_plan: Dict[str, int]
    solver_used: str
    optimization_energy: float
    optimization_runtime: float
    fallback_used: bool
    fallback_reason: Optional[str] = None
    applied: bool = True
    canonical_bitstring: Optional[str] = None
    qubit_count: int = 12
    qaoa_p: Optional[int] = None
    qaoa_shots: Optional[int] = None
    onehot_valid: bool = True
    emergency_valid: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert replanning event into a pure JSON-serializable dictionary."""
        return asdict(self)


class AdaptiveRollingHorizonController:
    """Closed-loop adaptive rolling-horizon signal controller for QuantumFlow.

    Observes live simulation queues at cycle boundaries, reconstructs the authoritative
    traffic QUBO, solves for the optimal timing plan using the existing Hybrid QAOA -> SA
    pipeline, and applies the new plan seamlessly for subsequent signal cycles.
    """

    def __init__(
        self,
        scenario: SimulationScenario,
        replan_interval: int = 60,
        qubo_config: Optional[FullQUBOConfig] = None,
        qaoa_p: int = 1,
        qaoa_maxiter: int = 30,
        qaoa_shots: int = 1024,
        sa_num_reads: int = 100,
        sa_num_sweeps: int = 1000,
        solver_seed: int = 42,
        nominal_capacity: float = 100.0,
    ):
        self.scenario = scenario
        self.replan_interval = replan_interval
        self.qubo_config = qubo_config if qubo_config is not None else FullQUBOConfig(
            onehot_penalty=100.0,
            wait_weight=2.0,
            capacity_weight=10.0,
            capacity_threshold=0.7,
            throughput_weight=1.0,
            service_rate=scenario.service_rate,
            coupling_weight=5.0,
            default_capacity=nominal_capacity,
            emergency_weight=0.0,  # Normal optimizer solves standard traffic distribution
            cross_street_weight=CROSS_STREET_WEIGHT if scenario.cross_street_rates else 0.0,
        )
        self.qaoa_p = qaoa_p
        self.qaoa_maxiter = qaoa_maxiter
        self.qaoa_shots = qaoa_shots
        self.sa_num_reads = sa_num_reads
        self.sa_num_sweeps = sa_num_sweeps
        self.solver_seed = solver_seed
        self.nominal_capacity = nominal_capacity

        self.validate_replan_interval()

        self.replan_events: List[ReplanningEvent] = []
        self.initial_plan: Optional[Dict[str, int]] = None
        self.current_plan: Optional[Dict[str, int]] = None
        self.cumulative_optimization_runtime: float = 0.0
        self.qaoa_execution_count: int = 0
        self.sa_fallback_count: int = 0

    def validate_replan_interval(self) -> None:
        """Validate replan interval compatibility with scenario cycle length."""
        if self.replan_interval <= 0:
            raise ValueError(f"replan_interval must be positive, got {self.replan_interval}.")
        if self.replan_interval % self.scenario.cycle_length != 0:
            raise ValueError(
                f"replan_interval ({self.replan_interval}s) must be an integer multiple of "
                f"scenario cycle_length ({self.scenario.cycle_length}s) to ensure safe cycle-boundary switching."
            )

    def should_replan(self, second: int) -> bool:
        """Check if second t is a scheduled replan boundary."""
        return second > 0 and (second % self.replan_interval == 0)

    def extract_traffic_state(
        self,
        current_queues: Dict[str, Union[int, float]],
        person_queues: Optional[Dict[str, float]] = None,
        approach_waiting_times: Optional[Dict[str, float]] = None,
    ) -> TrafficState:
        """Construct TrafficState from live simulator queues and optional person queues."""
        queues_clean: Dict[str, float] = {}
        densities_clean: Dict[str, float] = {}
        capacities_clean: Dict[str, float] = {}
        person_q_clean: Dict[str, float] = {}
        appr_w_clean: Dict[str, float] = {}

        for inter in self.scenario.intersections:
            q = float(current_queues.get(inter, 0.0))
            queues_clean[inter] = q
            densities_clean[inter] = min(0.95, max(0.20, q / 20.0))
            capacities_clean[inter] = self.nominal_capacity
            if person_queues and inter in person_queues:
                person_q_clean[inter] = float(person_queues[inter])
            if approach_waiting_times and inter in approach_waiting_times:
                appr_w_clean[inter] = float(approach_waiting_times[inter])

        return TrafficState(
            queues=queues_clean,
            densities=densities_clean,
            capacities=capacities_clean,
            person_queues=person_q_clean,
            approach_waiting_times=appr_w_clean,
            cross_rates={i: float(r) for i, r in self.scenario.cross_street_rates.items() if r > 0},
        )

    def generate_initial_plan(self, initial_queues: Optional[Dict[str, Union[int, float]]] = None) -> Dict[str, int]:
        """Generate and record initial normal signal plan at t=0."""
        queues = initial_queues if initial_queues is not None else self.scenario.initial_queues
        plan = self.replan(second=0, current_queues=queues, trigger="initial")
        self.initial_plan = dict(plan)
        return plan

    def replan(
        self,
        second: int,
        current_queues: Dict[str, Union[int, float]],
        trigger: str = "scheduled",
        person_queues: Optional[Dict[str, float]] = None,
        approach_waiting_times: Optional[Dict[str, float]] = None,
    ) -> Dict[str, int]:
        """Execute rolling-horizon replanning step from observed live queue state."""
        start_time = time.perf_counter()
        replan_idx = len(self.replan_events)

        traffic_state = self.extract_traffic_state(
            current_queues=current_queues,
            person_queues=person_queues,
            approach_waiting_times=approach_waiting_times,
        )

        # Build fresh QUBO directly from current observed traffic state
        qubo = build_qubo(
            traffic_state=traffic_state,
            emergency_constraints=None,
            config=self.qubo_config,
        )

        solve_seed = self.solver_seed + replan_idx

        # Solve using the authoritative Hybrid QAOA -> SA pipeline
        result: HybridSolveResult = solve_hybrid(
            qubo_model=qubo,
            emergency_constraints=None,
            qaoa_p=self.qaoa_p,
            qaoa_shots=self.qaoa_shots,
            qaoa_maxiter=self.qaoa_maxiter,
            sa_num_reads=self.sa_num_reads,
            sa_num_sweeps=self.sa_num_sweeps,
            seed=solve_seed,
        )

        elapsed = time.perf_counter() - start_time
        self.cumulative_optimization_runtime += elapsed

        if result.solver_used == "qaoa":
            self.qaoa_execution_count += 1
        elif result.solver_used == "sa":
            self.sa_fallback_count += 1

        # Record structured replanning telemetry
        chosen_plan = dict(result.signal_plan) if result.signal_plan else {"I1": 30, "I2": 30, "I3": 30, "I4": 30}
        event = ReplanningEvent(
            replan_index=replan_idx,
            simulation_time=second,
            trigger=trigger,
            queue_state=dict(traffic_state.queues),
            density_state=dict(traffic_state.densities),
            signal_plan=chosen_plan,
            solver_used=result.solver_used,
            optimization_energy=result.best_energy,
            optimization_runtime=result.runtime_seconds,
            fallback_used=result.fallback_used,
            fallback_reason=result.fallback_reason,
            applied=True,
            canonical_bitstring=result.best_bitstring,
            qubit_count=12,
            qaoa_p=self.qaoa_p,
            qaoa_shots=self.qaoa_shots,
            onehot_valid=result.onehot_valid,
            emergency_valid=result.emergency_valid,
        )
        self.replan_events.append(event)
        self.current_plan = chosen_plan

        return chosen_plan


    def step(
        self,
        t: int,
        current_queues: Dict[str, Union[int, float]],
        emergency_controller: Optional[Any] = None,
        person_queues: Optional[Dict[str, float]] = None,
        approach_waiting_times: Optional[Dict[str, float]] = None,
    ) -> Dict[str, int]:
        """Convenience simulation step hook called at each simulation tick.

        Returns newly optimized plan if t is a scheduled replan boundary; otherwise returns current plan.
        """
        if self.should_replan(t):
            new_plan = self.replan(
                second=t,
                current_queues=current_queues,
                trigger="scheduled",
                person_queues=person_queues,
                approach_waiting_times=approach_waiting_times,
            )
            return new_plan
        return self.current_plan if self.current_plan is not None else self.generate_initial_plan(current_queues)

    @property
    def scheduled_replan_count(self) -> int:
        """Count of periodic scheduled replans excluding initial t=0."""
        return sum(1 for e in self.replan_events if e.trigger == "scheduled")

    def events_as_dict(self) -> List[Dict[str, Any]]:
        """Return replanning events as list of JSON-safe dictionaries."""
        return [e.to_dict() for e in self.replan_events]

    def get_telemetry_summary(self) -> Dict[str, Any]:
        """Return aggregate telemetry statistics for all rolling-horizon replans."""
        return {
            "total_replans": len(self.replan_events),
            "replan_interval": self.replan_interval,
            "qaoa_execution_count": self.qaoa_execution_count,
            "sa_fallback_count": self.sa_fallback_count,
            "cumulative_optimization_runtime": round(self.cumulative_optimization_runtime, 4),
            "replan_timeline": [e.to_dict() for e in self.replan_events],
        }
