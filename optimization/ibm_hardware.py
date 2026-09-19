"""Simulator vs. (optional) real IBM quantum hardware for one small QUBO.

Takes an emergency-conflict QUBO (K=2 ambulances -> 4 qubits, K=3 -> 9 qubits), tunes QAOA
angles once on the ideal Aer simulator, then samples the *same* circuit with the *same* angles on:

    1. ideal   - noiseless Qiskit Aer
    2. noisy   - Qiskit Aer with a depolarising + readout noise model (always available, offline)
    3. hardware - a real IBM backend via ``qiskit-ibm-runtime`` (ONLY when ``use_hardware=True``)

and reports how noise degrades the answer. This module makes NO claim that hardware beats
classical solvers; the point is to show what the same optimisation looks like on a real device.

Hardware use is strictly opt-in: submitting a job spends the user's IBM quota and sends the
circuit to an external service, so nothing here contacts IBM unless ``use_hardware=True`` is
passed. Credentials come from the ``IBM_QUANTUM_TOKEN`` environment variable or an account
previously saved with ``QiskitRuntimeService.save_account``.
"""

from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional, Sequence
import math
import os
import time

import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error

from optimization.emergency_conflict import (
    EmergencyConflictRequest,
    build_conflict_qubo,
    decode_conflict_sequence,
    solve_conflict_exact,
)
from optimization.ising_converter import qubo_to_ising
from optimization.qaoa_solver import build_qaoa_circuit, qiskit_bitstring_to_bits, solve_tiny_qaoa
from optimization.qubo_model import QUBOModel

HONESTY_NOTE = (
    "Same circuit, same angles, different backends. This compares noise, not solution quality "
    "against classical solvers; no quantum advantage is claimed."
)

BASIS_GATES = ["rz", "sx", "x", "cx"]


@dataclass(frozen=True)
class BackendRun:
    """Outcome of sampling the tuned QAOA circuit on one backend."""

    kind: str  # "ideal" | "noisy" | "hardware"
    backend_name: str
    shots: int
    valid_fraction: float  # share of shots that decode to a valid ambulance ordering
    expected_energy: float  # mean QUBO energy over all shots (penalties included)
    best_energy: float  # lowest QUBO energy among *valid* sampled orderings (inf if none)
    optimal_probability: float  # share of shots that landed on the exact optimum
    best_sequence: List[str]
    tvd_vs_ideal: float  # total variation distance from the ideal distribution
    runtime_seconds: float
    job_id: Optional[str] = None
    note: str = ""
    top_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HardwareComparison:
    """Ideal vs noisy simulator (and optionally hardware) for one conflict QUBO."""

    num_qubits: int
    exact_energy: float
    exact_sequence: List[str]
    gamma: List[float]
    beta: List[float]
    circuit_depth_transpiled: int
    two_qubit_gate_count: int
    runs: Dict[str, BackendRun]
    hardware_requested: bool
    hardware_status: str
    honesty_note: str = HONESTY_NOTE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "num_qubits": self.num_qubits,
            "exact_energy": self.exact_energy,
            "exact_sequence": self.exact_sequence,
            "gamma": self.gamma,
            "beta": self.beta,
            "circuit_depth_transpiled": self.circuit_depth_transpiled,
            "two_qubit_gate_count": self.two_qubit_gate_count,
            "hardware_requested": self.hardware_requested,
            "hardware_status": self.hardware_status,
            "honesty_note": self.honesty_note,
            "runs": {k: v.to_dict() for k, v in self.runs.items()},
        }


def build_noise_model(p1: float = 0.001, p2: float = 0.02, readout: float = 0.02) -> NoiseModel:
    """Generic depolarising + readout noise, roughly in the range of current superconducting devices.

    These are illustrative defaults, not a calibrated model of any specific IBM backend.
    """
    nm = NoiseModel(basis_gates=BASIS_GATES)
    nm.add_all_qubit_quantum_error(depolarizing_error(p1, 1), ["sx", "x"])
    nm.add_all_qubit_quantum_error(depolarizing_error(p2, 2), ["cx"])
    nm.add_all_qubit_readout_error(ReadoutError([[1 - readout, readout], [readout, 1 - readout]]))
    return nm


def _normalise(counts: Dict[str, int]) -> Dict[str, float]:
    total = float(sum(counts.values()))
    return {k.replace(" ", ""): v / total for k, v in counts.items()}


def _tvd(p: Dict[str, float], q: Dict[str, float]) -> float:
    keys = set(p) | set(q)
    return 0.5 * sum(abs(p.get(k, 0.0) - q.get(k, 0.0)) for k in keys)


def _summarise(
    kind: str,
    backend_name: str,
    counts: Dict[str, int],
    qubo: QUBOModel,
    ids: Sequence[str],
    exact_energy: float,
    ideal_dist: Optional[Dict[str, float]],
    runtime: float,
    job_id: Optional[str] = None,
    note: str = "",
) -> BackendRun:
    K = len(ids)
    counts = {k.replace(" ", ""): int(v) for k, v in counts.items()}
    shots = sum(counts.values())
    valid_shots = 0
    optimal_shots = 0
    exp_e = 0.0
    best_e = float("inf")
    best_seq: List[str] = []
    for bitstr, cnt in counts.items():
        x = qiskit_bitstring_to_bits(bitstr)
        e = float(qubo.energy(x))
        exp_e += e * cnt / shots
        order = decode_conflict_sequence(x, K)
        if order is not None:
            valid_shots += cnt
            if e < best_e:
                best_e, best_seq = e, [ids[i] for i in order]
            if abs(e - exact_energy) < 1e-6:
                optimal_shots += cnt
    dist = _normalise(counts)
    top = dict(sorted(counts.items(), key=lambda kv: -kv[1])[:8])
    return BackendRun(
        kind=kind,
        backend_name=backend_name,
        shots=shots,
        valid_fraction=valid_shots / shots,
        expected_energy=exp_e,
        best_energy=best_e,
        optimal_probability=optimal_shots / shots,
        best_sequence=best_seq,
        tvd_vs_ideal=0.0 if ideal_dist is None else _tvd(dist, ideal_dist),
        runtime_seconds=runtime,
        job_id=job_id,
        note=note,
        top_counts=top,
    )


def _run_ibm_hardware(circuit, shots: int, backend_name: Optional[str], n_qubits: int):
    """Submit ``circuit`` to real IBM hardware. Returns (counts, backend_name, job_id, transpiled_circuit)."""
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

    token = os.environ.get("IBM_QUANTUM_TOKEN")
    service = (
        QiskitRuntimeService(channel="ibm_quantum_platform", token=token) if token else QiskitRuntimeService()
    )
    if backend_name:
        backend = service.backend(backend_name)
    else:
        backend = service.least_busy(operational=True, simulator=False, min_num_qubits=n_qubits)

    isa = generate_preset_pass_manager(backend=backend, optimization_level=1).run(circuit)
    job = SamplerV2(mode=backend).run([isa], shots=shots)
    result = job.result()
    counts = result[0].data.c.get_counts()  # classical register of build_qaoa_circuit is named "c"
    return counts, backend.name, job.job_id(), isa


def compare_simulator_vs_hardware(
    requests: Sequence[EmergencyConflictRequest],
    conflict_intersection: str = "I3",
    clearance_time_seconds: int = 6,
    shots: int = 4096,
    p: int = 2,
    maxiter: int = 60,
    seed: int = 42,
    noise_model: Optional[NoiseModel] = None,
    use_hardware: bool = False,
    backend_name: Optional[str] = None,
) -> HardwareComparison:
    """Run one small conflict QUBO on ideal Aer, noisy Aer and (opt-in) IBM hardware.

    Args:
        use_hardware: Must be True to contact IBM. Default False keeps everything offline.
        backend_name: Specific IBM backend (e.g. "ibm_brisbane"); default is the least busy device.
    """
    reqs = list(requests)
    K = len(reqs)
    if K < 2 or K > 3:
        raise ValueError("Hardware comparison supports 2 or 3 ambulances (4 or 9 qubits).")
    ids = [r.vehicle_id for r in reqs]

    qubo = build_conflict_qubo(reqs, conflict_intersection, clearance_time_seconds=clearance_time_seconds)
    exact_order, exact_e, _ = solve_conflict_exact(qubo, K)
    n = qubo.num_variables

    # 1. Tune angles once on the ideal simulator
    tuned = solve_tiny_qaoa(qubo, p=p, maxiter=maxiter, shots=shots, seed=seed)
    if tuned.status != "success":
        raise RuntimeError(f"QAOA parameter tuning failed: {tuned.error}")
    params = list(tuned.gamma) + list(tuned.beta)

    ising = qubo_to_ising(qubo)
    circuit, gammas, betas = build_qaoa_circuit(ising, p=p)
    bound = circuit.assign_parameters({**dict(zip(gammas, tuned.gamma)), **dict(zip(betas, tuned.beta))})

    runs: Dict[str, BackendRun] = {}

    # 2. Ideal simulator
    ideal_sim = AerSimulator(seed_simulator=seed)
    ideal_circ = transpile(bound, basis_gates=BASIS_GATES, optimization_level=1, seed_transpiler=seed)
    t0 = time.perf_counter()
    ideal_counts = ideal_sim.run(ideal_circ, shots=shots, seed_simulator=seed).result().get_counts()
    ideal_rt = time.perf_counter() - t0
    ideal_dist = _normalise(ideal_counts)
    runs["ideal"] = _summarise(
        "ideal", "aer_simulator", ideal_counts, qubo, ids, exact_e, None, ideal_rt,
        note="noiseless statevector-based sampling",
    )

    # 3. Noisy simulator
    nm = noise_model if noise_model is not None else build_noise_model()
    noisy_sim = AerSimulator(noise_model=nm, seed_simulator=seed)
    t0 = time.perf_counter()
    noisy_counts = noisy_sim.run(ideal_circ, shots=shots, seed_simulator=seed).result().get_counts()
    noisy_rt = time.perf_counter() - t0
    runs["noisy"] = _summarise(
        "noisy", "aer_simulator+noise", noisy_counts, qubo, ids, exact_e, ideal_dist, noisy_rt,
        note="generic depolarising (1q 0.1%, 2q 2%) + 2% readout error; illustrative, not a calibrated device model",
    )

    # 4. Real hardware (opt-in only)
    hardware_status = "not requested (offline run; pass use_hardware=True to submit to IBM)"
    if use_hardware:
        try:
            t0 = time.perf_counter()
            hw_counts, hw_name, job_id, _ = _run_ibm_hardware(bound, shots, backend_name, n)
            hw_rt = time.perf_counter() - t0
            runs["hardware"] = _summarise(
                "hardware", hw_name, hw_counts, qubo, ids, exact_e, ideal_dist, hw_rt, job_id=job_id,
                note="real device; runtime includes queue time",
            )
            hardware_status = f"completed on {hw_name} (job {job_id})"
        except ImportError:
            hardware_status = "unavailable: install qiskit-ibm-runtime (pip install -r requirements-ibm.txt)"
        except Exception as exc:  # credentials, queue, backend errors - never crash the caller
            hardware_status = f"failed: {type(exc).__name__}: {exc}"

    return HardwareComparison(
        num_qubits=n,
        exact_energy=float(exact_e),
        exact_sequence=[ids[i] for i in exact_order],
        gamma=[float(g) for g in tuned.gamma],
        beta=[float(b) for b in tuned.beta],
        circuit_depth_transpiled=int(ideal_circ.depth()),
        two_qubit_gate_count=int(ideal_circ.count_ops().get("cx", 0)),
        runs=runs,
        hardware_requested=use_hardware,
        hardware_status=hardware_status,
    )
