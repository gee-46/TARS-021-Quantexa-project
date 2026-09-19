"""Traffic Controller Adapters and Generic Interface for QuantumFlow Benchmarking.

Provides standardized controller abstractions for:
1. HybridController: Production QAOA with automated classical SA fallback.
2. SimulatedAnnealingController: Classical SA baseline (dwave-neal).
3. FixedTimeController: Deterministic static timing plan (e.g. 30s everywhere).
4. RuleBasedController: Deterministic threshold-based queue/density heuristic.

All controllers consume identical BenchmarkScenario structures and return standardized ControllerOutput objects.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, Any, Sequence
import time
import numpy as np

from optimization.variables import (
    INTERSECTIONS,
    DURATIONS,
    NUM_VARIABLES,
    get_variable_index,
)
from optimization.qubo_model import QUBOModel, qubo_energy
from optimization.decoder import (
    is_valid_onehot,
    is_valid_emergency,
    decode_solution,
)
from optimization.production_qaoa import ProductionQAOAResult
from optimization.sa_solver import (
    SimulatedAnnealingResult,
    solve_simulated_annealing,
)
from optimization.hybrid_solver import (
    HybridSolveResult,
    solve_hybrid,
)


def signal_plan_to_binary_vector(signal_plan: Dict[str, int]) -> Tuple[int, ...]:
    """Convert an intersection signal plan dictionary into a canonical 12-bit binary tuple.

    Args:
        signal_plan: Dictionary mapping intersection name to duration (e.g. {"I1": 30, ...}).

    Returns:
        Tuple[int, ...]: Canonical 12-element binary tuple {0, 1}^12.
    """
    x = [0] * NUM_VARIABLES
    for inter, dur in signal_plan.items():
        if inter in INTERSECTIONS and dur in DURATIONS:
            idx = get_variable_index(inter, dur)
            x[idx] = 1
    return tuple(x)


@dataclass(frozen=True)
class ControllerOutput:
    """Standardized output produced by any traffic controller adapter.

    Attributes:
        controller_name: Unique identifier of the controller.
        signal_plan: Decoded dictionary of green durations {"I1": 30, ...}.
        canonical_bitstring: Standard 12-bit string (x_0...x_11).
        binary_vector: Canonical binary decision tuple in {0, 1}^12.
        qubo_energy: Evaluated exact QUBO energy on the scenario's QUBOModel.
        runtime_seconds: Total wall-clock time spent in optimization / decision.
        onehot_valid: True if exactly 1 duration is active per intersection.
        emergency_valid: True if active emergency corridor requirements are satisfied.
        solver_used: Sub-solver used ('qaoa', 'sa', 'fixed', 'rule_based').
        fallback_used: True if hybrid fallback was triggered (or False/None).
        fallback_reason: Reason for fallback if applicable.
        raw_result: Optional underlying solver result object.
        error: Error message if controller execution failed.
    """

    controller_name: str
    signal_plan: Dict[str, int]
    canonical_bitstring: str
    binary_vector: Tuple[int, ...]
    qubo_energy: float
    runtime_seconds: float
    onehot_valid: bool
    emergency_valid: bool
    solver_used: Optional[str] = None
    fallback_used: Optional[bool] = None
    fallback_reason: Optional[str] = None
    raw_result: Optional[Any] = None
    error: Optional[str] = None


class BaseController(ABC):
    """Abstract base class establishing the generic interface for all traffic controllers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Controller identifier string."""
        pass

    @abstractmethod
    def solve(self, scenario: Any, seed: Optional[int] = None) -> ControllerOutput:
        """Solve or compute signal timing plan for the given benchmark scenario.

        Args:
            scenario: BenchmarkScenario instance containing traffic_state, qubo_model, emergency_constraints.
            seed: Optional deterministic random seed.

        Returns:
            ControllerOutput: Standardized controller decision output.
        """
        pass


class HybridController(BaseController):
    """Controller adapter for Hybrid QuantumFlow (QAOA primary + SA fallback)."""

    def __init__(
        self,
        name: str = "hybrid_quantumflow",
        qaoa_p: int = 1,
        qaoa_maxiter: int = 30,
        qaoa_shots: int = 1024,
        qaoa_timeout_seconds: float = 60.0,
        sa_num_reads: int = 100,
        sa_num_sweeps: int = 1000,
        require_onehot: bool = True,
        require_emergency_valid: bool = True,
    ):
        self._name = name
        self.qaoa_p = qaoa_p
        self.qaoa_maxiter = qaoa_maxiter
        self.qaoa_shots = qaoa_shots
        self.qaoa_timeout_seconds = qaoa_timeout_seconds
        self.sa_num_reads = sa_num_reads
        self.sa_num_sweeps = sa_num_sweeps
        self.require_onehot = require_onehot
        self.require_emergency_valid = require_emergency_valid

    @property
    def name(self) -> str:
        return self._name

    def solve(self, scenario: Any, seed: Optional[int] = None) -> ControllerOutput:
        run_seed = seed if seed is not None else 42
        res: HybridSolveResult = solve_hybrid(
            qubo_model=scenario.qubo_model,
            qaoa_p=self.qaoa_p,
            qaoa_maxiter=self.qaoa_maxiter,
            qaoa_shots=self.qaoa_shots,
            qaoa_seed=run_seed,
            qaoa_timeout_seconds=self.qaoa_timeout_seconds,
            sa_num_reads=self.sa_num_reads,
            sa_num_sweeps=self.sa_num_sweeps,
            sa_seed=run_seed,
            require_onehot=self.require_onehot,
            require_emergency_valid=self.require_emergency_valid,
            emergency_constraints=scenario.emergency_constraints,
        )

        plan = res.signal_plan if res.signal_plan is not None else {}
        return ControllerOutput(
            controller_name=self.name,
            signal_plan=plan,
            canonical_bitstring=res.best_bitstring,
            binary_vector=res.best_x,
            qubo_energy=res.qubo_energy,
            runtime_seconds=res.runtime_seconds,
            onehot_valid=res.onehot_valid,
            emergency_valid=res.emergency_valid,
            solver_used=res.solver_used,
            fallback_used=res.fallback_used,
            fallback_reason=res.fallback_reason,
            raw_result=res,
            error=res.error,
        )


class SimulatedAnnealingController(BaseController):
    """Controller adapter for Classical Simulated Annealing baseline (dwave-neal)."""

    def __init__(
        self,
        name: str = "classical_sa",
        num_reads: int = 100,
        num_sweeps: int = 1000,
    ):
        self._name = name
        self.num_reads = num_reads
        self.num_sweeps = num_sweeps

    @property
    def name(self) -> str:
        return self._name

    def solve(self, scenario: Any, seed: Optional[int] = None) -> ControllerOutput:
        run_seed = seed if seed is not None else 42
        res: SimulatedAnnealingResult = solve_simulated_annealing(
            qubo_model=scenario.qubo_model,
            num_reads=self.num_reads,
            num_sweeps=self.num_sweeps,
            seed=run_seed,
            emergency_constraints=scenario.emergency_constraints,
        )

        plan = res.signal_plan if res.signal_plan is not None else {}
        return ControllerOutput(
            controller_name=self.name,
            signal_plan=plan,
            canonical_bitstring=res.best_bitstring,
            binary_vector=res.best_x,
            qubo_energy=res.qubo_energy,
            runtime_seconds=res.runtime_seconds,
            onehot_valid=res.onehot_valid,
            emergency_valid=res.emergency_valid,
            solver_used="sa",
            fallback_used=False,
            fallback_reason=None,
            raw_result=res,
            error=res.error,
        )


class FixedTimeController(BaseController):
    """Deterministic fixed-time baseline traffic signal controller."""

    def __init__(
        self,
        name: str = "fixed_time_30s",
        default_duration: int = 30,
        custom_plan: Optional[Dict[str, int]] = None,
    ):
        self._name = name
        if custom_plan is not None:
            self.plan = dict(custom_plan)
        else:
            self.plan = {inter: default_duration for inter in INTERSECTIONS}

    @property
    def name(self) -> str:
        return self._name

    def solve(self, scenario: Any, seed: Optional[int] = None) -> ControllerOutput:
        start_time = time.perf_counter()
        x_vec = signal_plan_to_binary_vector(self.plan)
        bitstr = "".join(str(b) for b in x_vec)
        e_qubo = float(scenario.qubo_model.energy(x_vec, include_offset=True))
        runtime = time.perf_counter() - start_time

        valid_onehot = is_valid_onehot(x_vec)
        valid_emergency = is_valid_emergency(x_vec, scenario.emergency_constraints)

        return ControllerOutput(
            controller_name=self.name,
            signal_plan=dict(self.plan),
            canonical_bitstring=bitstr,
            binary_vector=x_vec,
            qubo_energy=e_qubo,
            runtime_seconds=runtime,
            onehot_valid=valid_onehot,
            emergency_valid=valid_emergency,
            solver_used="fixed",
            fallback_used=False,
            fallback_reason=None,
            raw_result=None,
            error=None,
        )


class RuleBasedController(BaseController):
    """Deterministic rule-based heuristic controller.

    Decision Rules (per intersection i):
    - If queue >= high_queue_threshold (30.0) OR density >= high_density_threshold (0.8) -> green = 45s
    - Elif queue >= med_queue_threshold (18.0) OR density >= med_density_threshold (0.5) -> green = 30s
    - Else -> green = 15s

    If respect_emergency is True and emergency constraints exist:
    - Route intersections are overridden to forced_duration (45s).
    """

    def __init__(
        self,
        name: str = "rule_based_actuated",
        high_queue_threshold: float = 30.0,
        med_queue_threshold: float = 18.0,
        high_density_threshold: float = 0.80,
        med_density_threshold: float = 0.50,
        respect_emergency: bool = False,
    ):
        self._name = name
        self.high_queue_threshold = high_queue_threshold
        self.med_queue_threshold = med_queue_threshold
        self.high_density_threshold = high_density_threshold
        self.med_density_threshold = med_density_threshold
        self.respect_emergency = respect_emergency

    @property
    def name(self) -> str:
        return self._name

    def solve(self, scenario: Any, seed: Optional[int] = None) -> ControllerOutput:
        start_time = time.perf_counter()
        traffic_state = scenario.traffic_state
        plan: Dict[str, int] = {}

        for inter in INTERSECTIONS:
            q = float(traffic_state.queues.get(inter, 0.0))
            d = float(traffic_state.densities.get(inter, 0.0))

            if q >= self.high_queue_threshold or d >= self.high_density_threshold:
                dur = 45
            elif q >= self.med_queue_threshold or d >= self.med_density_threshold:
                dur = 30
            else:
                dur = 15
            plan[inter] = dur

        if self.respect_emergency and scenario.emergency_constraints is not None:
            forced_dur = scenario.emergency_constraints.forced_duration
            for k in scenario.emergency_constraints.route:
                if k in plan:
                    plan[k] = forced_dur

        x_vec = signal_plan_to_binary_vector(plan)
        bitstr = "".join(str(b) for b in x_vec)
        e_qubo = float(scenario.qubo_model.energy(x_vec, include_offset=True))
        runtime = time.perf_counter() - start_time

        valid_onehot = is_valid_onehot(x_vec)
        valid_emergency = is_valid_emergency(x_vec, scenario.emergency_constraints)

        return ControllerOutput(
            controller_name=self.name,
            signal_plan=plan,
            canonical_bitstring=bitstr,
            binary_vector=x_vec,
            qubo_energy=e_qubo,
            runtime_seconds=runtime,
            onehot_valid=valid_onehot,
            emergency_valid=valid_emergency,
            solver_used="rule_based",
            fallback_used=False,
            fallback_reason=None,
            raw_result=None,
            error=None,
        )
