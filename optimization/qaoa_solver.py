"""Parameterized QAOA Implementation using Qiskit Aer and COBYLA.

Constructs explicit parameterized QAOA circuits for Ising spin Hamiltonians:
    |psi(gamma, beta)> = prod_{l=1}^p [ U_B(beta_l) U_C(gamma_l) ] |+>^n

Mathematical Components:
1. Initial State: |+>^n via Hadamard gates on all n qubits.
2. Cost Unitary U_C(gamma):
   - Linear terms h_i Z_i: RZ(2 * gamma * h_i) on qubit i
   - Quadratic terms J_ij Z_i Z_j: CX(i, j) -> RZ(2 * gamma * J_ij, j) -> CX(i, j)
3. Mixer Unitary U_B(beta):
   - RX(2 * beta) on each qubit i
4. Measurement: Standard computational basis measurement into classical register.

Execution Pipeline:
- Parameter optimization: Classical COBYLA minimizes expectation value <psi(gamma, beta)|H_C|psi(gamma, beta)>.
- Candidate selection: Samples distribution at optimal (gamma*, beta*), evaluates exact QUBO energy
  for all observed bitstrings, and selects the lowest-energy candidate.
"""

from dataclasses import dataclass, field
from typing import Sequence, Tuple, Dict, Any, List, Optional, Union
import itertools
import time
import numpy as np
from scipy.optimize import minimize

from qiskit import QuantumCircuit, transpile
from qiskit.circuit import Parameter
from qiskit_aer import AerSimulator

from optimization.qubo_model import QUBOModel, qubo_energy
from optimization.ising_converter import (
    IsingModel,
    bits_to_spins,
    spins_to_bits,
    ising_energy,
    qubo_to_ising,
)


def qiskit_bitstring_to_bits(bitstr: str) -> Tuple[int, ...]:
    """Convert a Qiskit measurement bitstring into a canonical binary tuple (x_0, x_1, ...).

    Qiskit Bitstring Convention:
        In Qiskit, bitstring characters are ordered from highest qubit index (n-1) at index 0
        to lowest qubit index (0) at index (n-1):
            bitstr = b_{n-1} b_{n-2} ... b_1 b_0
        Therefore, logical qubit i corresponds to bitstr[n - 1 - i].

    Args:
        bitstr: Measurement outcome string from Qiskit (e.g. '011').

    Returns:
        Tuple[int, ...]: Binary state tuple where index i corresponds to qubit i (x_0, x_1, ...).
    """
    n = len(bitstr)
    return tuple(int(bitstr[n - 1 - i]) for i in range(n))


def bits_to_qiskit_bitstring(bits: Sequence[int]) -> str:
    """Convert a canonical binary sequence (x_0, x_1, ...) to a Qiskit measurement bitstring.

    Args:
        bits: Binary sequence where index i corresponds to qubit i.

    Returns:
        str: Qiskit format bitstring b_{n-1}...b_0.
    """
    n = len(bits)
    return "".join(str(int(bits[n - 1 - i])) for i in range(n))


@dataclass(frozen=True)
class TinyQAOAResult:
    """Diagnostic result container for QAOA execution.

    Attributes:
        status: Execution status ('success' or 'failed').
        p: QAOA circuit depth / repetition count.
        gamma: Optimized gamma parameters.
        beta: Optimized beta parameters.
        expectation_value: Evaluated expectation value of the cost Hamiltonian at optimal parameters.
        counts: Raw measurement counts from Aer sampling at optimal parameters.
        best_bitstring: Qiskit bitstring of the lowest-energy sampled candidate.
        best_x: Binary decision vector (x_0, x_1, ...) of the lowest-energy candidate.
        best_energy: Exact QUBO objective energy of the lowest-energy sampled candidate.
        exact_optimum_energy: Exact theoretical global minimum energy from exhaustive ground truth.
        found_exact_optimum: True if lowest-energy candidate matches exact theoretical ground state.
        ground_state_probability: Fraction of total shots that measured the exact ground state.
        runtime: Wall-clock execution time in seconds.
        error: Error message if status is 'failed', else None.
    """

    status: str
    p: int
    gamma: List[float]
    beta: List[float]
    expectation_value: float
    counts: Dict[str, int]
    best_bitstring: str
    best_x: Tuple[int, ...]
    best_energy: float
    exact_optimum_energy: float
    found_exact_optimum: bool
    ground_state_probability: float
    runtime: float
    error: Optional[str] = None


def build_qaoa_circuit(ising_model: IsingModel, p: int = 1) -> Tuple[QuantumCircuit, List[Parameter], List[Parameter]]:
    """Build an explicit, parameterized QAOA quantum circuit decomposed for Qiskit Aer.

    Args:
        ising_model: IsingModel containing linear fields h and quadratic couplings J.
        p: Number of QAOA layers (depth).

    Returns:
        Tuple[QuantumCircuit, List[Parameter], List[Parameter]]:
            (circuit, gamma_parameters, beta_parameters)
    """
    n = ising_model.num_qubits
    qc = QuantumCircuit(n, n)

    # 1. Initial State Preparation: |+>^n
    for i in range(n):
        qc.h(i)

    gammas = [Parameter(f"gamma_{layer}") for layer in range(p)]
    betas = [Parameter(f"beta_{layer}") for layer in range(p)]

    for layer in range(p):
        gamma = gammas[layer]
        beta = betas[layer]

        # 2. Cost Unitary: U_C(gamma) = exp(-i * gamma * H_C)
        # Linear terms: h_i * Z_i -> RZ(2 * gamma * h_i)
        for i in range(n):
            h_i = float(ising_model.h[i])
            if not np.isclose(h_i, 0.0):
                # RZ(theta) = exp(-i * theta / 2 * Z) -> theta = 2 * gamma * h_i
                qc.rz(2.0 * gamma * h_i, i)

        # Quadratic terms: J_ij * Z_i Z_j -> CX(i, j) -> RZ(2 * gamma * J_ij, j) -> CX(i, j)
        for (i, j), J_ij in ising_model.J.items():
            if not np.isclose(J_ij, 0.0):
                qc.cx(i, j)
                qc.rz(2.0 * gamma * J_ij, j)
                qc.cx(i, j)

        # 3. Mixer Unitary: U_B(beta) = exp(-i * beta * sum_i X_i)
        # RX(theta) = exp(-i * theta / 2 * X) -> theta = 2 * beta
        for i in range(n):
            qc.rx(2.0 * beta, i)

    # 4. Measurement
    for i in range(n):
        qc.measure(i, i)

    return qc, gammas, betas


def solve_tiny_qaoa(
    qubo_model: QUBOModel,
    p: int = 1,
    maxiter: int = 30,
    shots: int = 1024,
    seed: int = 42,
    initial_params: Optional[Sequence[float]] = None,
) -> TinyQAOAResult:
    """Solve a tiny QUBO problem using parameterized QAOA on Qiskit Aer with COBYLA.

    Args:
        qubo_model: Target QUBOModel.
        p: QAOA circuit depth (default 1).
        maxiter: Maximum COBYLA parameter optimization iterations (default 30).
        shots: Measurement shot count for sampling (default 1024).
        seed: Deterministic random seed for simulator and optimizer.
        initial_params: Optional initial parameter sequence [gamma_0, ..., beta_0, ...].

    Returns:
        TinyQAOAResult: Complete structured optimization result with exact verification.
    """
    start_time = time.perf_counter()

    try:
        # 1. Transform QUBO to Ising
        ising_model = qubo_to_ising(qubo_model)
        n = ising_model.num_qubits

        # 2. Compute exact ground truth by exhaustive enumeration
        all_states = [tuple(bits) for bits in itertools.product([0, 1], repeat=n)]
        exact_energies = [qubo_model.energy(x, include_offset=True) for x in all_states]
        exact_optimum_energy = float(min(exact_energies))
        exact_optimum_states = {
            all_states[idx] for idx, e in enumerate(exact_energies) if np.isclose(e, exact_optimum_energy)
        }

        # 3. Build QAOA circuit
        qc, gammas, betas = build_qaoa_circuit(ising_model, p=p)
        param_list = gammas + betas

        # 4. Transpile onto AerSimulator
        sim = AerSimulator(seed_simulator=seed)
        transpiled_qc = transpile(qc, sim)

        # 5. Define expectation objective function for COBYLA
        def expectation_loss(params: Sequence[float]) -> float:
            param_dict = {param_list[k]: float(params[k]) for k in range(len(param_list))}
            bound_circ = transpiled_qc.assign_parameters(param_dict)
            job = sim.run(bound_circ, shots=shots, seed_simulator=seed)
            counts = job.result().get_counts()
            total_shots = sum(counts.values())

            # Evaluate expected Ising energy
            exp_val = 0.0
            for bitstr, cnt in counts.items():
                x_cand = qiskit_bitstring_to_bits(bitstr)
                z_cand = bits_to_spins(x_cand)
                e_ising = ising_energy(z_cand, ising_model)
                exp_val += e_ising * (cnt / float(total_shots))

            return float(exp_val)

        # 6. Initial parameter vector
        if initial_params is not None:
            x0 = np.asarray(initial_params, dtype=np.float64)
        else:
            # Standard heuristic starting point: gamma in [0.2, 0.8], beta in [0.2, 0.8]
            rng = np.random.default_rng(seed)
            x0 = rng.uniform(0.2, 0.8, size=2 * p)

        # 7. Optimize parameters via COBYLA
        opt_res = minimize(
            expectation_loss,
            x0,
            method="COBYLA",
            options={"maxiter": maxiter},
        )
        opt_params = opt_res.x

        # 8. Final sampling at optimal parameters
        opt_param_dict = {param_list[k]: float(opt_params[k]) for k in range(len(param_list))}
        final_bound_circ = transpiled_qc.assign_parameters(opt_param_dict)
        final_job = sim.run(final_bound_circ, shots=shots, seed_simulator=seed)
        final_counts = final_job.result().get_counts()
        total_final_shots = sum(final_counts.values())

        # 9. Evaluate candidate states using the ORIGINAL QUBO energy
        best_x: Optional[Tuple[int, ...]] = None
        best_bitstr: Optional[str] = None
        best_energy = float("inf")
        ground_state_count = 0

        for bitstr, cnt in final_counts.items():
            x_cand = qiskit_bitstring_to_bits(bitstr)
            e_cand = qubo_model.energy(x_cand, include_offset=True)

            if x_cand in exact_optimum_states:
                ground_state_count += cnt

            if e_cand < best_energy:
                best_energy = e_cand
                best_x = x_cand
                best_bitstr = bitstr

        if best_x is None or best_bitstr is None:
            raise RuntimeError("No candidate bitstrings sampled from QAOA.")

        found_exact = np.isclose(best_energy, exact_optimum_energy)
        ground_state_prob = ground_state_count / float(total_final_shots)
        runtime = time.perf_counter() - start_time

        return TinyQAOAResult(
            status="success",
            p=p,
            gamma=[float(g) for g in opt_params[:p]],
            beta=[float(b) for b in opt_params[p:]],
            expectation_value=float(opt_res.fun),
            counts=final_counts,
            best_bitstring=best_bitstr,
            best_x=best_x,
            best_energy=float(best_energy),
            exact_optimum_energy=exact_optimum_energy,
            found_exact_optimum=bool(found_exact),
            ground_state_probability=float(ground_state_prob),
            runtime=runtime,
            error=None,
        )

    except Exception as e:
        runtime = time.perf_counter() - start_time
        return TinyQAOAResult(
            status="failed",
            p=p,
            gamma=[],
            beta=[],
            expectation_value=0.0,
            counts={},
            best_bitstring="",
            best_x=(),
            best_energy=float("inf"),
            exact_optimum_energy=0.0,
            found_exact_optimum=False,
            ground_state_probability=0.0,
            runtime=runtime,
            error=str(e),
        )
