"""Production 12-Qubit QAOA Solver for QuantumFlow Traffic Optimization.

Executes parameterized Quantum Approximate Optimization Algorithm (QAOA) on Qiskit Aer
to solve the multi-intersection traffic QUBO objective:
    QUBOModel -> IsingModel -> Parameterized 12-Qubit QAOA Circuit -> AerSimulator -> COBYLA -> Candidate Evaluation

Key Design Features:
- Direct Ingestion: Operates directly on supplied QUBOModel adhering strictly to canonical 12 variables.
- Explicit Gate-Level Construction: Parameterized |+>^12 initial state, RZ + CX-RZ-CX cost unitary, RX mixer unitary.
- True Hamiltonian Expectation: COBYLA optimizes <psi(gamma, beta)| H_C |psi(gamma, beta)> including exact Ising constant.
- Strict Candidate Evaluation: Evaluates all sampled candidates using original QUBO energy x^T Q x + offset (NOT by frequency).
- Timeout Protection: Non-blocking timeout guard terminating gracefully with status="timeout".
- Comprehensive Diagnostics: Reports best canonical state, validity classification, signal plan, and QUBO/Ising energies.
"""

from dataclasses import dataclass, field
from typing import Sequence, Tuple, Dict, Any, List, Optional, Union
import time
import numpy as np
from scipy.optimize import minimize

from qiskit import QuantumCircuit, transpile
from qiskit.circuit import Parameter
from qiskit_aer import AerSimulator

from optimization.variables import NUM_VARIABLES, VARIABLE_NAMES
from optimization.qubo_model import QUBOModel, qubo_energy
from optimization.ising_converter import (
    IsingModel,
    bits_to_spins,
    spins_to_bits,
    ising_energy,
    qubo_to_ising,
)
from optimization.decoder import (
    is_valid_onehot,
    is_valid_emergency,
    decode_solution,
)
from optimization.qaoa_solver import (
    qiskit_bitstring_to_bits,
    bits_to_qiskit_bitstring,
    build_qaoa_circuit,
)


@dataclass(frozen=True)
class ProductionQAOAResult:
    """Production-grade structured output from the 12-qubit QAOA solver.

    Attributes:
        status: Execution status ('success', 'timeout', or 'failed').
        error: Detailed error description if execution failed, else None.
        p: QAOA circuit repetition depth.
        num_qubits: Total qubit count (12).
        maxiter: Maximum parameter optimization iterations allocated.
        optimization_iterations: Number of optimization function evaluations performed.
        shots: Number of measurement shots per evaluation and final sampling.
        optimized_parameters: List of optimized [gamma_0, ..., beta_0, ...] angles.
        expectation_value: Final evaluated expectation value of H_C at optimal angles.
        counts: Full measurement outcome counts dictionary from AerSimulator.
        best_bitstring: Qiskit format measurement string of lowest-energy candidate.
        best_canonical_bitstring: Standard canonical 12-bit string (x_0...x_11).
        best_x: Binary decision vector tuple of lowest-energy candidate in {0, 1}^12.
        best_z: Spin vector tuple of lowest-energy candidate in {-1, +1}^12.
        best_energy: Exact QUBO objective energy of the lowest-energy candidate.
        qubo_energy: Redundant confirmation of exact QUBO energy.
        ising_energy: Evaluated Ising Hamiltonian energy for the best spin configuration.
        onehot_valid: True if candidate satisfies exactly 1 active duration per intersection.
        emergency_valid: True if candidate satisfies active emergency corridor route.
        signal_plan: Decoded dictionary {"I1": dur, ...} if onehot_valid, else None.
        runtime_seconds: Total wall-clock execution time in seconds.
        timed_out: True if timeout limit was triggered during execution.
        ground_state_probability: Fraction of measurement shots matching best candidate.
    """

    status: str
    error: Optional[str]
    p: int
    num_qubits: int
    maxiter: int
    optimization_iterations: int
    shots: int
    optimized_parameters: List[float]
    expectation_value: float
    counts: Dict[str, int]
    best_bitstring: str
    best_canonical_bitstring: str
    best_x: Tuple[int, ...]
    best_z: Tuple[int, ...]
    best_energy: float
    qubo_energy: float
    ising_energy: float
    onehot_valid: bool
    emergency_valid: bool
    signal_plan: Optional[Dict[str, int]]
    runtime_seconds: float
    timed_out: bool
    ground_state_probability: float = 0.0
    exact_optimum_sampled: Optional[bool] = None


def solve_production_qaoa(
    qubo_model: QUBOModel,
    p: int = 1,
    maxiter: int = 30,
    shots: int = 1024,
    seed: int = 42,
    timeout_seconds: float = 60.0,
    initial_params: Optional[Sequence[float]] = None,
    emergency_constraints: Optional[Any] = None,
    exact_optimum_x: Optional[Sequence[int]] = None,
) -> ProductionQAOAResult:
    """Solve the 12-variable QuantumFlow QUBO using parameterized QAOA on Qiskit Aer.

    Args:
        qubo_model: Target upper-triangular QUBOModel.
        p: QAOA circuit depth (default 1).
        maxiter: Max COBYLA iterations (default 30).
        shots: Measurement shot count for sampling (default 1024).
        seed: Deterministic simulator and initialization seed (default 42).
        timeout_seconds: Maximum wall-clock time in seconds before terminating (default 60.0).
        initial_params: Optional initial [gamma, beta] parameter vector (defaults to 0.1 for all parameters).
        emergency_constraints: Optional active EmergencyConstraints instance.
        exact_optimum_x: Optional exact binary ground state tuple for diagnostic validation.

    Returns:
        ProductionQAOAResult: Comprehensive, structured QAOA optimization result.
    """
    start_time = time.perf_counter()
    n = qubo_model.num_variables
    iteration_counter = 0

    try:
        # 1. Transform QUBO to Ising representation
        ising_model = qubo_to_ising(qubo_model)

        # 2. Construct explicit parameterized circuit
        qc, gammas, betas = build_qaoa_circuit(ising_model, p=p)
        param_list = gammas + betas

        # 3. Transpile onto AerSimulator
        sim = AerSimulator(seed_simulator=seed)
        transpiled_qc = transpile(qc, sim)

        # 4. State tracking for timeout protection
        best_interim_counts: Dict[str, int] = {}
        interim_best_params = [0.1] * (2 * p)

        def expectation_loss(params: Sequence[float]) -> float:
            nonlocal iteration_counter, best_interim_counts, interim_best_params
            iteration_counter += 1

            # Check timeout
            elapsed = time.perf_counter() - start_time
            if elapsed > timeout_seconds:
                raise TimeoutError(
                    f"QAOA execution exceeded timeout threshold of {timeout_seconds:.2f}s "
                    f"(elapsed: {elapsed:.2f}s, iterations: {iteration_counter})."
                )

            param_dict = {param_list[k]: float(params[k]) for k in range(len(param_list))}
            bound_circ = transpiled_qc.assign_parameters(param_dict)
            job = sim.run(bound_circ, shots=shots, seed_simulator=seed)
            counts = job.result().get_counts()
            best_interim_counts = counts
            interim_best_params = list(params)

            total_shots = sum(counts.values())
            exp_val = 0.0
            for bitstr, cnt in counts.items():
                x_cand = qiskit_bitstring_to_bits(bitstr)
                z_cand = bits_to_spins(x_cand)
                e_ising = ising_energy(z_cand, ising_model)
                exp_val += e_ising * (cnt / float(total_shots))

            return float(exp_val)

        # 5. Initialize parameters deterministically (default gamma=0.1, beta=0.1)
        if initial_params is not None:
            x0 = np.asarray(initial_params, dtype=np.float64)
        else:
            x0 = np.full(2 * p, 0.1, dtype=np.float64)

        # 6. Run COBYLA Parameter Optimization with Timeout Guard
        timed_out = False
        opt_params = x0
        exp_val_final = 0.0

        try:
            opt_res = minimize(
                expectation_loss,
                x0,
                method="COBYLA",
                options={"maxiter": maxiter},
            )
            opt_params = opt_res.x
            exp_val_final = float(opt_res.fun)
        except TimeoutError:
            timed_out = True
            opt_params = np.array(interim_best_params, dtype=np.float64)

        # 7. Final Measurement Sampling at Best Parameters
        elapsed_after_opt = time.perf_counter() - start_time
        if not timed_out and elapsed_after_opt < timeout_seconds:
            opt_param_dict = {param_list[k]: float(opt_params[k]) for k in range(len(param_list))}
            final_bound = transpiled_qc.assign_parameters(opt_param_dict)
            final_job = sim.run(final_bound, shots=shots, seed_simulator=seed)
            final_counts = final_job.result().get_counts()
        else:
            final_counts = best_interim_counts

        if not final_counts:
            # Fallback if no counts sampled before timeout
            timed_out = True
            final_counts = {bits_to_qiskit_bitstring([0] * n): shots}

        # 8. Evaluate all sampled candidates using ORIGINAL QUBO energy
        # Select candidate with minimum QUBO energy (tie-break lexicographically by canonical bitstring)
        total_final_shots = sum(final_counts.values())
        candidate_evaluations: List[Tuple[float, str, str, Tuple[int, ...], Tuple[int, ...]]] = []

        for bitstr, cnt in final_counts.items():
            x_cand = qiskit_bitstring_to_bits(bitstr)
            z_cand = tuple(int(z) for z in bits_to_spins(x_cand))
            canonical_str = "".join(str(b) for b in x_cand)
            e_qubo = float(qubo_model.energy(x_cand, include_offset=True))
            candidate_evaluations.append((e_qubo, canonical_str, bitstr, x_cand, z_cand))

        # Sort primarily by QUBO energy ascending, secondarily by canonical bitstring
        candidate_evaluations.sort(key=lambda item: (item[0], item[1]))

        best_e_qubo, best_canonical_str, best_bitstr, best_x, best_z = candidate_evaluations[0]
        best_ising_e = float(ising_model.energy(best_z))

        # Ground state / best candidate probability in final sampling distribution
        exact_optimum_sampled = None
        if exact_optimum_x is not None:
            exact_bitstr = bits_to_qiskit_bitstring(exact_optimum_x)
            exact_count = final_counts.get(exact_bitstr, 0)
            exact_optimum_sampled = exact_bitstr in final_counts
            ground_state_prob = exact_count / float(total_final_shots) if total_final_shots > 0 else 0.0
        else:
            best_shot_count = final_counts.get(best_bitstr, 0)
            ground_state_prob = best_shot_count / float(total_final_shots) if total_final_shots > 0 else 0.0

        # 9. Validity and Signal Plan Decoding
        valid_onehot = is_valid_onehot(best_x)
        valid_emergency = is_valid_emergency(best_x, emergency_constraints)
        signal_plan = decode_solution(best_x) if valid_onehot else None

        runtime = time.perf_counter() - start_time
        status = "timeout" if timed_out else "success"

        return ProductionQAOAResult(
            status=status,
            error=None if not timed_out else "Execution terminated early due to timeout limit.",
            p=p,
            num_qubits=n,
            maxiter=maxiter,
            optimization_iterations=iteration_counter,
            shots=shots,
            optimized_parameters=[float(v) for v in opt_params],
            expectation_value=exp_val_final,
            counts=final_counts,
            best_bitstring=best_bitstr,
            best_canonical_bitstring=best_canonical_str,
            best_x=best_x,
            best_z=best_z,
            best_energy=best_e_qubo,
            qubo_energy=best_e_qubo,
            ising_energy=best_ising_e,
            onehot_valid=valid_onehot,
            emergency_valid=valid_emergency,
            signal_plan=signal_plan,
            runtime_seconds=runtime,
            timed_out=timed_out,
            ground_state_probability=ground_state_prob,
            exact_optimum_sampled=exact_optimum_sampled,
        )

    except Exception as e:
        runtime = time.perf_counter() - start_time
        return ProductionQAOAResult(
            status="failed",
            error=str(e),
            p=p,
            num_qubits=n,
            maxiter=maxiter,
            optimization_iterations=iteration_counter,
            shots=shots,
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
            runtime_seconds=runtime,
            timed_out=False,
            ground_state_probability=0.0,
        )
