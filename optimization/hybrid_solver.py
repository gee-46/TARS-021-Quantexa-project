"""Hybrid QAOA + Classical Simulated Annealing Fallback Orchestrator for QuantumFlow.

Provides a robust, fault-tolerant orchestration pipeline:
1. Always attempts production 12-qubit QAOA on Qiskit Aer first.
2. Validates the returned QAOA candidate against operational constraints (finite energy, one-hot, emergency).
3. If QAOA succeeds and satisfies constraints, returns the QAOA result directly (without invoking SA).
4. If QAOA times out, fails, or produces an operationally invalid candidate, automatically triggers
   Classical Simulated Annealing (dwave-neal) on the exact same QUBOModel.
5. Returns a structured, fully traceable HybridSolveResult preserving diagnostics from both solvers.
"""

from dataclasses import dataclass
from typing import Sequence, Tuple, Dict, Any, List, Optional
import time
import numpy as np

from optimization.qubo_model import QUBOModel, qubo_energy
from optimization.decoder import (
    is_valid_onehot,
    is_valid_emergency,
    decode_solution,
)
from optimization.production_qaoa import (
    ProductionQAOAResult,
    solve_production_qaoa,
)
from optimization.sa_solver import (
    SimulatedAnnealingResult,
    solve_simulated_annealing,
)


@dataclass(frozen=True)
class HybridSolveResult:
    """Production-grade structured output from the Hybrid Optimization Orchestrator.

    Attributes:
        status: Execution status ('success' or 'failed').
        solver_used: Solver that produced the final accepted answer ('qaoa' or 'sa').
        fallback_used: True if classical SA fallback was triggered, False if QAOA was accepted.
        fallback_reason: Explanation for triggering fallback (None if QAOA was accepted).
            Possible reasons: 'qaoa_timeout', 'qaoa_failed', 'invalid_candidate',
            'non_finite_energy', 'invalid_onehot', 'invalid_emergency'.
        qaoa_result: Full diagnostic result from QAOA execution (or None if QAOA could not run).
        sa_result: Full diagnostic result from SA execution (None if fallback was not invoked).
        best_bitstring: Canonical 12-bit string (x_0...x_11) of accepted final solution.
        best_x: Binary decision tuple (x_0, ..., x_11) of accepted final solution.
        best_energy: Exact evaluated QUBO energy (x^T Q x + offset) of the accepted solution.
        qubo_energy: Redundant confirmation of exact QUBO energy.
        onehot_valid: True if accepted candidate satisfies one active duration per intersection.
        emergency_valid: True if accepted candidate satisfies active emergency corridor route.
        signal_plan: Decoded timing plan dictionary {"I1": 45, ...} if onehot_valid, else None.
        runtime_seconds: Total cumulative wall-clock execution time in seconds.
        error: Detailed error description if execution failed completely, else None.
    """

    status: str
    solver_used: str
    fallback_used: bool
    fallback_reason: Optional[str]
    qaoa_result: Optional[ProductionQAOAResult]
    sa_result: Optional[SimulatedAnnealingResult]
    best_bitstring: str
    best_x: Tuple[int, ...]
    best_energy: float
    qubo_energy: float
    onehot_valid: bool
    emergency_valid: bool
    signal_plan: Optional[Dict[str, int]]
    runtime_seconds: float
    error: Optional[str] = None

    @property
    def plan(self) -> Optional[Dict[str, int]]:
        return self.signal_plan

    @property
    def energy(self) -> float:
        return self.best_energy


def solve_hybrid(
    qubo_model: Optional[QUBOModel] = None,
    qaoa_p: int = 1,
    qaoa_maxiter: int = 30,
    qaoa_shots: int = 1024,
    qaoa_seed: int = 42,
    qaoa_timeout_seconds: float = 60.0,
    sa_num_reads: int = 100,
    sa_num_sweeps: int = 1000,
    sa_seed: int = 42,
    require_onehot: bool = True,
    require_emergency_valid: bool = True,
    emergency_constraints: Optional[Any] = None,
    **kwargs: Any,
) -> HybridSolveResult:
    """Orchestrate hybrid optimization: QAOA first, with classical Simulated Annealing fallback."""
    if qubo_model is None:
        if "qubo" in kwargs:
            qubo_model = kwargs.pop("qubo")
        else:
            raise ValueError("qubo_model must be provided to solve_hybrid.")

    if "seed" in kwargs and kwargs["seed"] is not None:
        s = int(kwargs.pop("seed"))
        qaoa_seed = s
        sa_seed = s

    start_time = time.perf_counter()

    # 1. Attempt Production QAOA First
    qaoa_res: Optional[ProductionQAOAResult] = None
    fallback_reason: Optional[str] = None


    try:
        qaoa_res = solve_production_qaoa(
            qubo_model=qubo_model,
            p=qaoa_p,
            maxiter=qaoa_maxiter,
            shots=qaoa_shots,
            seed=qaoa_seed,
            timeout_seconds=qaoa_timeout_seconds,
            emergency_constraints=emergency_constraints,
            **kwargs,
        )
    except Exception as e:
        fallback_reason = "qaoa_failed"
        qaoa_res = ProductionQAOAResult(
            status="failed",
            error=str(e),
            p=qaoa_p,
            num_qubits=getattr(qubo_model, "num_variables", 12),
            maxiter=qaoa_maxiter,
            optimization_iterations=0,
            shots=qaoa_shots,
            optimized_parameters=[],
            expectation_value=0.0,
            counts={},
            best_bitstring="",
            best_canonical_bitstring="",
            best_x=(),
            best_z=(),
            best_energy=float("inf"),
            qubo_energy=float("inf"),
            ising_energy=float("inf"),
            onehot_valid=False,
            emergency_valid=False,
            signal_plan=None,
            runtime_seconds=time.perf_counter() - start_time,
            timed_out=False,
            ground_state_probability=0.0,
        )

    # 2. Inspect QAOA Result and Validate Candidate
    if fallback_reason is None and qaoa_res is not None:
        if qaoa_res.timed_out or qaoa_res.status == "timeout":
            fallback_reason = "qaoa_timeout"
        elif qaoa_res.status != "success":
            fallback_reason = "qaoa_failed"
        elif not qaoa_res.best_x or len(qaoa_res.best_x) != qubo_model.num_variables:
            fallback_reason = "invalid_candidate"
        elif not all(b in (0, 1) for b in qaoa_res.best_x):
            fallback_reason = "invalid_candidate"
        else:
            # Re-evaluate exact QUBO energy from original formulation
            e_qubo = float(qubo_model.energy(qaoa_res.best_x, include_offset=True))
            if np.isnan(e_qubo) or np.isinf(e_qubo):
                fallback_reason = "non_finite_energy"
            elif require_onehot and not is_valid_onehot(qaoa_res.best_x):
                fallback_reason = "invalid_onehot"
            elif (
                require_emergency_valid
                and emergency_constraints is not None
                and not is_valid_emergency(qaoa_res.best_x, emergency_constraints)
            ):
                fallback_reason = "invalid_emergency"
            else:
                # Candidate is fully accepted!
                fallback_reason = None

    # 3. If QAOA Candidate is Accepted -> Return QAOA Result (No SA invoked)
    if fallback_reason is None and qaoa_res is not None:
        runtime = time.perf_counter() - start_time
        e_qubo = float(qubo_model.energy(qaoa_res.best_x, include_offset=True))
        valid_onehot = is_valid_onehot(qaoa_res.best_x)
        valid_emergency = is_valid_emergency(qaoa_res.best_x, emergency_constraints)
        signal_plan = decode_solution(qaoa_res.best_x) if valid_onehot else None

        return HybridSolveResult(
            status="success",
            solver_used="qaoa",
            fallback_used=False,
            fallback_reason=None,
            qaoa_result=qaoa_res,
            sa_result=None,
            best_bitstring=qaoa_res.best_canonical_bitstring,
            best_x=qaoa_res.best_x,
            best_energy=e_qubo,
            qubo_energy=e_qubo,
            onehot_valid=valid_onehot,
            emergency_valid=valid_emergency,
            signal_plan=signal_plan,
            runtime_seconds=runtime,
            error=None,
        )

    # 4. Fallback Triggered -> Execute Classical Simulated Annealing on EXACT SAME QUBO
    sa_res = solve_simulated_annealing(
        qubo_model=qubo_model,
        num_reads=sa_num_reads,
        num_sweeps=sa_num_sweeps,
        seed=sa_seed,
        emergency_constraints=emergency_constraints,
    )

    runtime = time.perf_counter() - start_time

    if sa_res.status == "success" and sa_res.best_x:
        e_qubo_sa = float(qubo_model.energy(sa_res.best_x, include_offset=True))
        valid_onehot_sa = is_valid_onehot(sa_res.best_x)
        valid_emergency_sa = is_valid_emergency(sa_res.best_x, emergency_constraints)
        signal_plan_sa = decode_solution(sa_res.best_x) if valid_onehot_sa else None

        # Check SA validity against required operational constraints
        sa_valid = True
        if require_onehot and not valid_onehot_sa:
            sa_valid = False
        if require_emergency_valid and emergency_constraints is not None and not valid_emergency_sa:
            sa_valid = False
        if np.isnan(e_qubo_sa) or np.isinf(e_qubo_sa):
            sa_valid = False

        status_sa = "success" if sa_valid else "failed"
        err_sa = None if sa_valid else f"SA fallback returned invalid candidate (onehot={valid_onehot_sa}, emergency={valid_emergency_sa})."

        return HybridSolveResult(
            status=status_sa,
            solver_used="sa",
            fallback_used=True,
            fallback_reason=fallback_reason,
            qaoa_result=qaoa_res,
            sa_result=sa_res,
            best_bitstring=sa_res.best_bitstring,
            best_x=sa_res.best_x,
            best_energy=e_qubo_sa,
            qubo_energy=e_qubo_sa,
            onehot_valid=valid_onehot_sa,
            emergency_valid=valid_emergency_sa,
            signal_plan=signal_plan_sa,
            runtime_seconds=runtime,
            error=err_sa,
        )

    # Both QAOA and SA failed
    return HybridSolveResult(
        status="failed",
        solver_used="sa",
        fallback_used=True,
        fallback_reason=fallback_reason,
        qaoa_result=qaoa_res,
        sa_result=sa_res,
        best_bitstring="",
        best_x=(),
        best_energy=float("inf"),
        qubo_energy=float("inf"),
        onehot_valid=False,
        emergency_valid=False,
        signal_plan=None,
        runtime_seconds=runtime,
        error=f"QAOA failed ({fallback_reason}) and SA fallback also failed: {sa_res.error}",
    )
