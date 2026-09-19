"""Classical Simulated Annealing Solver Baseline for QuantumFlow.

Consumes the exact same upper-triangular QUBOModel used by QAOA and executes
simulated annealing using dwave-neal (SimulatedAnnealingSampler) and dimod (BinaryQuadraticModel).

Key Principles:
1. Exact Formulation Equivalence: Consumes the exact same QUBO matrix Q, offset, and variable ordering.
2. Direct BQM Translation:
   - linear[i] = Q[i, i]
   - quadratic[(i, j)] = Q[i, j] for i < j (strictly NOT doubled)
   - offset = qubo_model.offset
   - Vartype: dimod.BINARY
3. True QUBO Evaluation: Evaluates all sampled states on the original QUBO energy objective (x^T Q x + offset)
   and selects the lowest-energy candidate (tie-break lexicographically by canonical bitstring).
4. No Traffic Bias: Does not inject artificial constraints or repair solutions during optimization.
"""

from dataclasses import dataclass, field
from typing import Sequence, Tuple, Dict, Any, List, Optional, Union
import time
import numpy as np
import dimod
import neal

from optimization.variables import NUM_VARIABLES, VARIABLE_NAMES
from optimization.qubo_model import QUBOModel, qubo_energy
from optimization.decoder import (
    is_valid_onehot,
    is_valid_emergency,
    decode_solution,
)


def qubo_to_bqm(qubo_model: QUBOModel) -> dimod.BinaryQuadraticModel:
    """Convert an upper-triangular QUBOModel into an exact dimod BinaryQuadraticModel.

    Strict Mapping Rules:
    - Linear terms: linear[i] = Q[i, i]
    - Quadratic terms: quadratic[(i, j)] = Q[i, j] for i < j (not multiplied by 2)
    - Offset: offset = qubo_model.offset
    - Vartype: dimod.BINARY ({0, 1})

    Args:
        qubo_model: Source upper-triangular QUBOModel.

    Returns:
        dimod.BinaryQuadraticModel: Mathematically equivalent BQM representation.
    """
    Q = qubo_model.Q
    n = qubo_model.num_variables
    offset = float(qubo_model.offset)

    linear: Dict[int, float] = {}
    quadratic: Dict[Tuple[int, int], float] = {}

    for i in range(n):
        q_ii = float(Q[i, i])
        if not np.isclose(q_ii, 0.0):
            linear[i] = q_ii

    for i in range(n):
        for j in range(i + 1, n):
            q_ij = float(Q[i, j])
            if not np.isclose(q_ij, 0.0):
                quadratic[(i, j)] = q_ij

    return dimod.BinaryQuadraticModel(linear, quadratic, offset, dimod.BINARY)


@dataclass(frozen=True)
class SimulatedAnnealingResult:
    """Structured result container for Classical Simulated Annealing execution.

    Attributes:
        status: Execution status ('success' or 'failed').
        error: Detailed error message if status is 'failed', else None.
        num_reads: Total annealing reads/runs requested.
        num_sweeps: Monte Carlo sweeps per annealing run.
        seed: Random seed provided to the sampler.
        num_variables: Number of decision variables (12).
        best_bitstring: Canonical 12-bit string (x_0...x_11) of lowest-energy candidate.
        best_x: Binary decision tuple (x_0, ..., x_11) of lowest-energy candidate.
        best_energy: Exact original QUBO energy (x^T Q x + offset) of the best candidate.
        qubo_energy: Exact QUBO energy confirmation.
        bqm_energy: BQM energy reported by dimod for the best candidate.
        runtime_seconds: Total wall-clock execution time in seconds.
        samples_considered: Number of unique or total candidate states evaluated.
        sample_distribution: Dictionary mapping canonical bitstring -> occurrence count.
        onehot_valid: True if candidate satisfies one duration per intersection.
        emergency_valid: True if candidate satisfies emergency corridor constraints.
        signal_plan: Decoded dictionary of green durations {"I1": 45, ...} if onehot_valid, else None.
        exact_optimum_found: Optional diagnostic flag indicating if exact ground state was sampled.
        optimality_gap: Optional energy difference (best_energy - exact_optimum_energy).
        exact_optimum_energy: Optional exact theoretical ground state energy for validation.
    """

    status: str
    error: Optional[str]
    num_reads: int
    num_sweeps: int
    seed: Optional[int]
    num_variables: int
    best_bitstring: str
    best_x: Tuple[int, ...]
    best_energy: float
    qubo_energy: float
    bqm_energy: float
    runtime_seconds: float
    samples_considered: int
    sample_distribution: Dict[str, int]
    onehot_valid: bool
    emergency_valid: bool
    signal_plan: Optional[Dict[str, int]]
    exact_optimum_found: Optional[bool] = None
    optimality_gap: Optional[float] = None
    exact_optimum_energy: Optional[float] = None


def solve_simulated_annealing(
    qubo_model: QUBOModel,
    num_reads: int = 100,
    num_sweeps: int = 1000,
    seed: Optional[int] = 42,
    emergency_constraints: Optional[Any] = None,
    exact_optimum_x: Optional[Sequence[int]] = None,
    exact_optimum_energy: Optional[float] = None,
    **sampler_kwargs: Any,
) -> SimulatedAnnealingResult:
    """Solve the 12-variable QuantumFlow QUBO using classical simulated annealing (dwave-neal).

    Args:
        qubo_model: Target upper-triangular QUBOModel.
        num_reads: Number of independent annealing trajectory reads (default 100).
        num_sweeps: Number of sweeps per read (default 1000).
        seed: Deterministic random seed for reproducibility (default 42).
        emergency_constraints: Optional active EmergencyConstraints instance for validity decoding.
        exact_optimum_x: Optional exact binary ground state tuple for diagnostic verification.
        exact_optimum_energy: Optional exact ground state energy for optimality gap calculation.
        **sampler_kwargs: Additional arguments passed to neal.SimulatedAnnealingSampler.sample.

    Returns:
        SimulatedAnnealingResult: Structured result container.
    """
    start_time = time.perf_counter()
    n = 0

    try:
        if qubo_model is None or not hasattr(qubo_model, "num_variables"):
            raise ValueError(f"Expected a valid QUBOModel instance, got: {qubo_model}")

        n = qubo_model.num_variables

        # 1. Transform QUBO into BQM
        bqm = qubo_to_bqm(qubo_model)

        # 2. Instantiate neal sampler
        sampler = neal.SimulatedAnnealingSampler()

        # 3. Sample the BQM
        sampleset = sampler.sample(
            bqm,
            num_reads=num_reads,
            num_sweeps=num_sweeps,
            seed=seed,
            **sampler_kwargs,
        )

        # 4. Evaluate all returned candidate samples using the ORIGINAL QUBO objective
        sample_counts: Dict[str, int] = {}
        candidate_evaluations: List[Tuple[float, str, Tuple[int, ...], float, int]] = []

        for datum in sampleset.data(["sample", "energy", "num_occurrences"]):
            sample_dict = datum.sample
            bqm_e = float(datum.energy)
            num_occ = int(datum.num_occurrences)

            # Map sample dictionary {0: b_0, 1: b_1, ...} to canonical binary tuple (x_0, ..., x_{n-1})
            x_cand = tuple(int(sample_dict.get(i, 0)) for i in range(n))
            canonical_bitstr = "".join(str(b) for b in x_cand)

            # Track distribution
            sample_counts[canonical_bitstr] = sample_counts.get(canonical_bitstr, 0) + num_occ

            # Compute exact original QUBO energy
            qubo_e = float(qubo_model.energy(x_cand, include_offset=True))
            candidate_evaluations.append((qubo_e, canonical_bitstr, x_cand, bqm_e, num_occ))

        if not candidate_evaluations:
            raise RuntimeError("Simulated annealing returned empty sampleset.")

        # 5. Candidate Selection: strictly by minimum original QUBO energy
        # Tie-break deterministically lexicographically by canonical bitstring
        candidate_evaluations.sort(key=lambda item: (item[0], item[1]))

        best_qubo_e, best_canonical_str, best_x, best_bqm_e, _ = candidate_evaluations[0]

        # 6. Validity and Signal Plan Decoding
        valid_onehot = is_valid_onehot(best_x)
        valid_emergency = is_valid_emergency(best_x, emergency_constraints)
        signal_plan = decode_solution(best_x) if valid_onehot else None

        # 7. Optional exact optimum validation metrics
        exact_found = None
        gap = None
        if exact_optimum_x is not None:
            exact_canonical = "".join(str(b) for b in exact_optimum_x)
            exact_found = best_canonical_str == exact_canonical
        elif exact_optimum_energy is not None:
            exact_found = np.isclose(best_qubo_e, exact_optimum_energy)

        if exact_optimum_energy is not None:
            gap = float(best_qubo_e - exact_optimum_energy)

        runtime = time.perf_counter() - start_time

        return SimulatedAnnealingResult(
            status="success",
            error=None,
            num_reads=num_reads,
            num_sweeps=num_sweeps,
            seed=seed,
            num_variables=n,
            best_bitstring=best_canonical_str,
            best_x=best_x,
            best_energy=best_qubo_e,
            qubo_energy=best_qubo_e,
            bqm_energy=best_bqm_e,
            runtime_seconds=runtime,
            samples_considered=len(candidate_evaluations),
            sample_distribution=sample_counts,
            onehot_valid=valid_onehot,
            emergency_valid=valid_emergency,
            signal_plan=signal_plan,
            exact_optimum_found=exact_found,
            optimality_gap=gap,
            exact_optimum_energy=exact_optimum_energy,
        )

    except Exception as e:
        runtime = time.perf_counter() - start_time
        return SimulatedAnnealingResult(
            status="failed",
            error=str(e),
            num_reads=num_reads,
            num_sweeps=num_sweeps,
            seed=seed,
            num_variables=n,
            best_bitstring="",
            best_x=(),
            best_energy=float("inf"),
            qubo_energy=float("inf"),
            bqm_energy=float("inf"),
            runtime_seconds=runtime,
            samples_considered=0,
            sample_distribution={},
            onehot_valid=False,
            emergency_valid=False,
            signal_plan=None,
            exact_optimum_found=False,
            optimality_gap=None,
            exact_optimum_energy=exact_optimum_energy,
        )


# Backward-compatible alias
solve_sa = solve_simulated_annealing
