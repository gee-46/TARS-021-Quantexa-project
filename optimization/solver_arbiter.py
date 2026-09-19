"""Multi-Solver Arbiter and Comparative Evaluation for QuantumFlow.

Evaluates and compares multiple optimization algorithms on the IDENTICAL 12-variable QUBO model:
1. QAOA: 12-Qubit gate-level parameterized quantum circuit simulation on Qiskit Aer.
2. Simulated Annealing: Classical thermal sampling via dwave-neal.
3. Greedy Local Search: Deterministic classical single-bit/coordinate descent baseline.

Properties:
- Pure, unmanipulated scoring based strictly on evaluated QUBO energy: E(x) = x^T Q x + offset.
- Independent execution ensuring no solver contaminates another's execution or timing.
- Feasibility checks (One-Hot validity across 4 intersections, Emergency constraints).
- Objective ranking identifying the best feasible candidate.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Sequence, Tuple
import time
import numpy as np

from optimization.variables import NUM_VARIABLES, INTERSECTIONS, DURATIONS, get_variable_index
from optimization.qubo_model import QUBOModel
from optimization.decoder import decode_solution, is_valid_onehot, is_valid_emergency
from optimization.production_qaoa import solve_production_qaoa, ProductionQAOAResult
from optimization.sa_solver import solve_simulated_annealing, SimulatedAnnealingResult



@dataclass(frozen=True)
class SolverCandidateRecord:
    """Standardized result record for a single solver evaluating a QUBO instance.

    Attributes:
        solver_name: Name identifier ("qaoa", "sa", "greedy").
        candidate_bitstring: Binary decision string x in {0, 1}^12.
        signal_plan: Decoded green durations {"I1": 30, ...}.
        qubo_energy: Exact objective energy E(x).
        runtime_seconds: Wall-clock execution time in seconds.
        onehot_valid: True if candidate assigns exactly one duration per intersection.
        emergency_valid: True if candidate respects all emergency route allocations.
        is_feasible: True if candidate is fully valid for deployment.
    """

    solver_name: str
    candidate_bitstring: str
    signal_plan: Dict[str, int]
    qubo_energy: float
    runtime_seconds: float
    onehot_valid: bool
    emergency_valid: bool
    is_feasible: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArbiterComparisonResult:
    """Unified comparative benchmark result across all evaluated solvers.

    Attributes:
        candidates: Map of solver name to its SolverCandidateRecord.
        best_solver: Name of the feasible solver achieving lowest QUBO energy.
        best_plan: Optimal feasible signal plan.
        best_energy: Energy of the winning feasible candidate.
        qaoa_energy: Energy achieved by QAOA.
        sa_energy: Energy achieved by Simulated Annealing.
        greedy_energy: Energy achieved by Greedy Local Search.
        qaoa_runtime: Runtime of QAOA in seconds.
        sa_runtime: Runtime of SA in seconds.
        greedy_runtime: Runtime of Greedy in seconds.
        qaoa_vs_sa_energy_delta: qaoa_energy - sa_energy (0.0 = tie, >0.0 = SA better).
        qaoa_vs_greedy_energy_delta: qaoa_energy - greedy_energy.
    """

    candidates: Dict[str, SolverCandidateRecord]
    best_solver: str
    best_plan: Dict[str, int]
    best_energy: float
    qaoa_energy: float
    sa_energy: float
    greedy_energy: float
    qaoa_runtime: float
    sa_runtime: float
    greedy_runtime: float
    qaoa_vs_sa_energy_delta: float
    qaoa_vs_greedy_energy_delta: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "best_solver": self.best_solver,
            "best_plan": self.best_plan,
            "best_energy": self.best_energy,
            "qaoa_energy": self.qaoa_energy,
            "sa_energy": self.sa_energy,
            "greedy_energy": self.greedy_energy,
            "qaoa_runtime": self.qaoa_runtime,
            "sa_runtime": self.sa_runtime,
            "greedy_runtime": self.greedy_runtime,
            "qaoa_vs_sa_energy_delta": self.qaoa_vs_sa_energy_delta,
            "qaoa_vs_greedy_energy_delta": self.qaoa_vs_greedy_energy_delta,
            "candidates": {k: v.to_dict() for k, v in self.candidates.items()},
        }


def solve_greedy(qubo: QUBOModel) -> Tuple[np.ndarray, float, float]:
    """Execute greedy single-variable coordinate descent on the 12-variable QUBO."""
    start_t = time.perf_counter()

    # Start with standard nominal one-hot configuration: 30s green across all 4 nodes
    # indices for 30s: I1->1, I2->4, I3->7, I4->10
    best_x = np.zeros(NUM_VARIABLES, dtype=int)
    for inter in INTERSECTIONS:
        best_x[get_variable_index(inter, 30)] = 1

    best_e = qubo.energy(best_x)

    # Greedily search each intersection's 3 duration choices
    improved = True
    iterations = 0
    max_iter = 10

    while improved and iterations < max_iter:
        improved = False
        iterations += 1
        for inter in INTERSECTIONS:
            current_choice = None
            for dur in DURATIONS:
                idx = get_variable_index(inter, dur)
                if best_x[idx] == 1:
                    current_choice = dur
                    break

            for dur in DURATIONS:
                if dur == current_choice:
                    continue
                cand_x = best_x.copy()
                for d_other in DURATIONS:
                    cand_x[get_variable_index(inter, d_other)] = 0
                cand_x[get_variable_index(inter, dur)] = 1

                cand_e = qubo.energy(cand_x)
                if cand_e < best_e:
                    best_e = cand_e
                    best_x = cand_x
                    improved = True

    runtime = time.perf_counter() - start_t
    return best_x, best_e, runtime


def arbitrate_solvers(
    qubo: QUBOModel,
    emergency_constraints: Optional[Dict[str, int]] = None,
    qaoa_p: int = 1,
    qaoa_shots: int = 1024,
    qaoa_maxiter: int = 30,
    sa_reads: int = 100,
    sa_sweeps: int = 1000,
    seed: int = 42,
) -> ArbiterComparisonResult:
    """Solve the identical QUBO using QAOA, Simulated Annealing, and Greedy Local Search."""
    records: Dict[str, SolverCandidateRecord] = {}

    # 1. QAOA Execution
    try:
        qaoa_res = solve_production_qaoa(
            qubo_model=qubo,
            p=qaoa_p,
            shots=qaoa_shots,
            maxiter=qaoa_maxiter,
            seed=seed,
            emergency_constraints=emergency_constraints,
        )
        qaoa_sample = qaoa_res.best_x
        qaoa_energy = qaoa_res.best_energy
        qaoa_runtime = qaoa_res.runtime_seconds
        qaoa_str = qaoa_res.best_canonical_bitstring
        plan_qaoa = qaoa_res.signal_plan if qaoa_res.signal_plan is not None else (decode_solution(qaoa_sample) if qaoa_res.onehot_valid else {})
        oh_qaoa = qaoa_res.onehot_valid
        em_qaoa = qaoa_res.emergency_valid
    except Exception:
        qaoa_sample = (0,) * NUM_VARIABLES
        qaoa_energy = float("inf")
        qaoa_runtime = 0.0
        qaoa_str = "0" * NUM_VARIABLES
        plan_qaoa = {}
        oh_qaoa = False
        em_qaoa = False

    records["qaoa"] = SolverCandidateRecord(
        solver_name="qaoa",
        candidate_bitstring=qaoa_str,
        signal_plan=plan_qaoa,
        qubo_energy=qaoa_energy,
        runtime_seconds=qaoa_runtime,
        onehot_valid=oh_qaoa,
        emergency_valid=em_qaoa,
        is_feasible=oh_qaoa and em_qaoa,
    )

    # 2. Simulated Annealing Execution
    sa_res = solve_simulated_annealing(
        qubo_model=qubo,
        num_reads=sa_reads,
        num_sweeps=sa_sweeps,
        seed=seed,
        emergency_constraints=emergency_constraints,
    )
    sa_sample = sa_res.best_x
    sa_energy = sa_res.best_energy
    sa_runtime = sa_res.runtime_seconds
    sa_str = sa_res.best_bitstring
    plan_sa = sa_res.signal_plan if sa_res.signal_plan is not None else (decode_solution(sa_sample) if sa_res.onehot_valid else {})
    oh_sa = sa_res.onehot_valid
    em_sa = sa_res.emergency_valid

    records["sa"] = SolverCandidateRecord(
        solver_name="sa",
        candidate_bitstring=sa_str,
        signal_plan=plan_sa,
        qubo_energy=sa_energy,
        runtime_seconds=sa_runtime,
        onehot_valid=oh_sa,
        emergency_valid=em_sa,
        is_feasible=oh_sa and em_sa,
    )


    # 3. Greedy Local Search Execution
    greedy_sample, greedy_energy, greedy_runtime = solve_greedy(qubo)
    greedy_str = "".join(str(int(b)) for b in greedy_sample)

    oh_greedy = is_valid_onehot(greedy_sample)
    plan_greedy = decode_solution(greedy_sample) if oh_greedy else {}
    em_greedy = is_valid_emergency(greedy_sample, emergency_constraints) if emergency_constraints else True
    records["greedy"] = SolverCandidateRecord(
        solver_name="greedy",
        candidate_bitstring=greedy_str,
        signal_plan=plan_greedy,
        qubo_energy=greedy_energy,
        runtime_seconds=greedy_runtime,
        onehot_valid=oh_greedy,
        emergency_valid=em_greedy,
        is_feasible=oh_greedy and em_greedy,
    )

    # 4. Objective Arbiter Decision
    # Filter feasible solvers
    feasible_solvers = [r for r in records.values() if r.is_feasible]
    if feasible_solvers:
        best_cand = min(feasible_solvers, key=lambda r: r.qubo_energy)
    else:
        best_cand = min(records.values(), key=lambda r: r.qubo_energy)

    return ArbiterComparisonResult(
        candidates=records,
        best_solver=best_cand.solver_name,
        best_plan=best_cand.signal_plan,
        best_energy=best_cand.qubo_energy,
        qaoa_energy=qaoa_energy,
        sa_energy=sa_energy,
        greedy_energy=greedy_energy,
        qaoa_runtime=qaoa_runtime,
        sa_runtime=sa_runtime,
        greedy_runtime=greedy_runtime,
        qaoa_vs_sa_energy_delta=round(qaoa_energy - sa_energy, 6),
        qaoa_vs_greedy_energy_delta=round(qaoa_energy - greedy_energy, 6),
    )
