"""Emergency Conflict Detection and Multi-Emergency Conflict QUBO Formulation.

When 2 or more emergency vehicles simultaneously request conflicting green preemption
at shared or opposing network intersections (e.g. Emergency A on I1->I2->I3 and
Emergency B on I4->I3->I2 contending for I3), this module:
1. Detects junction and temporal corridor conflicts.
2. Formulates a dedicated sequence-prioritization Emergency Conflict QUBO.
3. Solves via QAOA, Simulated Annealing, Greedy or exact enumeration (arbiter).
4. Produces a safe, conflict-free priority schedule for the emergency runtime controller.

Mathematical Conflict QUBO Formulation:
- Binary decision variables y_{e, s} in {0, 1} indicating whether vehicle e is assigned priority sequence slot s in {0, 1, ..., K-1}.
- Sequence One-Hot Constraint:
    H_onehot = P_seq * ( sum_s (sum_e y_{e, s} - 1)^2 + sum_e (sum_s y_{e, s} - 1)^2 )
- Weighted Delay & Priority Objective (packed-slot wait model):
    start_s = t0 + s * (clearance_time + 1),  t0 = earliest arrival among contenders
    wait_{e,s} = max(0, start_s - arrival_e)
    H_delay = sum_{e, s} priority_weight_e * wait_{e,s} * y_{e, s},  priority_weight_e = 1 / priority_level_e
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple, Optional, Any, Sequence, Set
import itertools
import time
import numpy as np

from optimization.qubo_model import QUBOModel
from optimization.sa_solver import solve_sa


@dataclass(frozen=True)
class EmergencyConflictRequest:
    """Active emergency vehicle request participating in corridor arbitration.

    Attributes:
        vehicle_id: Unique emergency vehicle identifier.
        route: Sequence of intersections traversed.
        current_intersection: Current intersection being approached or queued at.
        distance_to_conflict: Number of steps remaining to reach the contested junction.
        estimated_arrival_at_conflict: Estimated simulation second of arrival at junction.
        priority_level: Priority tier (1 = highest, 2 = standard).
    """

    vehicle_id: str
    route: Tuple[str, ...]
    current_intersection: str
    distance_to_conflict: int
    estimated_arrival_at_conflict: int
    priority_level: int = 1


@dataclass(frozen=True)
class EmergencyConflictSchedule:
    """Conflict-free sequencing plan produced by the conflict optimization solver.

    Attributes:
        conflict_intersection: Contested junction ID (e.g. "I3").
        sequenced_vehicles: Ordered list of vehicle IDs in clearance sequence order.
        clearance_intervals: Estimated time window assigned to each vehicle.
        solver_used: Optimization solver used ("qaoa", "sa", or "rule_based").
        qubo_energy: Energy of the selected sequencing bitstring.
        is_feasible: True if no conflicting simultaneous greens are granted.
    """

    conflict_intersection: str
    sequenced_vehicles: List[str]
    clearance_intervals: Dict[str, Tuple[int, int]]
    solver_used: str
    qubo_energy: float
    is_feasible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def detect_emergency_conflicts(
    requests: Sequence[EmergencyConflictRequest],
    contested_lookahead_seconds: int = 15,
) -> Dict[str, List[EmergencyConflictRequest]]:
    """Detect intersections where multiple emergency vehicles will arrive concurrently."""
    intersection_requests: Dict[str, List[EmergencyConflictRequest]] = {}

    for req in requests:
        for idx, inter in enumerate(req.route):
            # Check if this intersection is ahead of or at current step
            curr_idx = req.route.index(req.current_intersection) if req.current_intersection in req.route else 0
            if idx >= curr_idx:
                if inter not in intersection_requests:
                    intersection_requests[inter] = []
                intersection_requests[inter].append(req)

    # Filter for contested junctions with 2+ concurrent requests
    conflicts: Dict[str, List[EmergencyConflictRequest]] = {}
    for inter, req_list in intersection_requests.items():
        if len(req_list) >= 2:
            # Check temporal overlap
            arr_times = [r.estimated_arrival_at_conflict for r in req_list]
            if max(arr_times) - min(arr_times) <= contested_lookahead_seconds:
                conflicts[inter] = req_list

    return conflicts


def build_conflict_qubo(
    requests: Sequence[EmergencyConflictRequest],
    conflict_intersection: str,
    clearance_time_seconds: int = 6,
    onehot_penalty: float = 50.0,
) -> QUBOModel:
    """Construct a dedicated Emergency Conflict QUBO for sequencing K requests.

    Variables y_{e,s} (index e*K + s) say "vehicle e clears the junction in slot s".
    One-hot penalties force a permutation; the linear term is the priority-weighted
    waiting time each (vehicle, slot) pairing causes. The penalty is raised automatically
    when needed so that no one-hot violation can be cheaper than a valid sequence.
    """
    K = len(requests)
    num_vars = K * K  # y_{e, s} for e in 0..K-1, s in 0..K-1
    Q = np.zeros((num_vars, num_vars), dtype=float)
    offset = 0.0

    def idx(e: int, s: int) -> int:
        return e * K + s

    # 1. Delay & priority costs (computed first so the penalty can dominate them)
    t0 = float(min(r.estimated_arrival_at_conflict for r in requests)) if requests else 0.0
    slot_pitch = float(clearance_time_seconds + 1)
    costs = np.zeros((K, K), dtype=float)
    for e, req in enumerate(requests):
        weight = 1.0 / float(max(1, req.priority_level))  # priority 1 = most urgent = highest delay weight
        for s in range(K):
            start = t0 + s * slot_pitch
            costs[e, s] = weight * max(0.0, start - float(req.estimated_arrival_at_conflict))

    penalty = max(float(onehot_penalty), 2.0 * float(costs.max() if K else 0.0) + 1.0)

    # 2. One-Hot Constraints:
    # Each slot s has exactly one vehicle: sum_e y_{e, s} = 1 -> (sum_e y_{e,s} - 1)^2
    for s in range(K):
        for e1 in range(K):
            k1 = idx(e1, s)
            Q[k1, k1] += penalty * (-1.0)
            for e2 in range(e1 + 1, K):
                k2 = idx(e2, s)
                Q[k1, k2] += penalty * 2.0
        offset += penalty * 1.0

    # Each vehicle e has exactly one slot: sum_s y_{e, s} = 1 -> (sum_s y_{e,s} - 1)^2
    for e in range(K):
        for s1 in range(K):
            k1 = idx(e, s1)
            Q[k1, k1] += penalty * (-1.0)
            for s2 in range(s1 + 1, K):
                k2 = idx(e, s2)
                Q[k1, k2] += penalty * 2.0
        offset += penalty * 1.0

    # 3. Linear delay cost
    for e in range(K):
        for s in range(K):
            Q[idx(e, s), idx(e, s)] += costs[e, s]

    variable_order = tuple(f"y_{e}_{s}" for e in range(K) for s in range(K))
    return QUBOModel(
        Q=Q,
        variable_order=variable_order,
        offset=offset,
        metadata={"type": "emergency_conflict", "intersection": conflict_intersection, "K": K, "penalty": penalty},
    )


def decode_conflict_sequence(x: Sequence[int], num_vehicles: int) -> Optional[List[int]]:
    """Decode y_{e,s} into request indices ordered by slot; None if x is not a permutation."""
    K = num_vehicles
    if len(x) != K * K:
        return None
    order: List[Optional[int]] = [None] * K
    for e in range(K):
        slots = [s for s in range(K) if x[e * K + s] == 1]
        if len(slots) != 1 or order[slots[0]] is not None:
            return None
        order[slots[0]] = e
    if any(o is None for o in order):
        return None
    return [int(o) for o in order if o is not None]


def _sequence_to_bits(order: Sequence[int]) -> Tuple[int, ...]:
    K = len(order)
    bits = [0] * (K * K)
    for slot, e in enumerate(order):
        bits[e * K + slot] = 1
    return tuple(bits)


@dataclass(frozen=True)
class ConflictSolverRecord:
    """One solver's answer to the same emergency-conflict QUBO."""

    solver_name: str
    sequence: List[str]
    energy: float
    runtime_seconds: float
    is_valid: bool
    is_optimal: bool
    note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ConflictArbiterResult:
    """QAOA vs SA vs Greedy (vs exact ground truth) on one emergency-conflict QUBO."""

    conflict_intersection: str
    num_qubits: int
    records: Dict[str, ConflictSolverRecord]
    exact_energy: float
    winner: str
    verdict: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_intersection": self.conflict_intersection,
            "num_qubits": self.num_qubits,
            "exact_energy": self.exact_energy,
            "winner": self.winner,
            "verdict": self.verdict,
            "records": {k: v.to_dict() for k, v in self.records.items()},
        }


def solve_conflict_greedy(requests: Sequence[EmergencyConflictRequest]) -> Tuple[List[int], float]:
    """Greedy baseline: highest priority first, then earliest arrival."""
    start = time.perf_counter()
    order = sorted(
        range(len(requests)),
        key=lambda e: (requests[e].priority_level, requests[e].estimated_arrival_at_conflict, e),
    )
    return order, time.perf_counter() - start


def solve_conflict_exact(qubo: QUBOModel, num_vehicles: int) -> Tuple[List[int], float, float]:
    """Exhaustive search over all K! valid permutations (ground truth)."""
    start = time.perf_counter()
    best_order: List[int] = []
    best_e = float("inf")
    for perm in itertools.permutations(range(num_vehicles)):
        e = qubo.energy(_sequence_to_bits(perm))
        if e < best_e - 1e-12:
            best_e, best_order = e, list(perm)
    return best_order, best_e, time.perf_counter() - start


def arbitrate_conflict(
    requests: Sequence[EmergencyConflictRequest],
    conflict_intersection: str,
    clearance_time_seconds: int = 6,
    qaoa_p: int = 2,
    qaoa_shots: int = 2048,
    qaoa_maxiter: int = 60,
    seed: int = 42,
    include_qaoa: bool = True,
) -> ConflictArbiterResult:
    """Solve the identical conflict QUBO with QAOA, SA and Greedy and report who won.

    The verdict is computed from energies alone: if QAOA loses or ties, it says so.
    Exact enumeration provides ground truth. K <= 4 keeps QAOA at <= 16 qubits.
    """
    from optimization.qaoa_solver import solve_tiny_qaoa

    reqs = list(requests)
    K = len(reqs)
    if K < 2:
        raise ValueError("Conflict arbitration needs at least two emergency requests.")
    if K > 4:
        raise ValueError("Conflict arbitration supports at most 4 simultaneous vehicles (K^2 <= 16 qubits).")

    qubo = build_conflict_qubo(reqs, conflict_intersection, clearance_time_seconds=clearance_time_seconds)
    ids = [r.vehicle_id for r in reqs]

    _, exact_e, _ = solve_conflict_exact(qubo, K)

    def record(name: str, x: Sequence[int], runtime: float, note: str = "") -> ConflictSolverRecord:
        order = decode_conflict_sequence(x, K)
        energy = float(qubo.energy(x))
        valid = order is not None
        return ConflictSolverRecord(
            solver_name=name,
            sequence=[ids[e] for e in order] if order is not None else [],
            energy=energy,
            runtime_seconds=float(runtime),
            is_valid=valid,
            is_optimal=bool(valid and abs(energy - exact_e) < 1e-6),
            note=note,
        )

    records: Dict[str, ConflictSolverRecord] = {}

    if include_qaoa:
        q = solve_tiny_qaoa(qubo, p=qaoa_p, maxiter=qaoa_maxiter, shots=qaoa_shots, seed=seed)
        if q.status == "success":
            records["qaoa"] = record(
                "qaoa", q.best_x, q.runtime,
                note=f"p={qaoa_p}, {qaoa_shots} shots, ground-state prob {q.ground_state_probability:.3f} (Aer simulator)",
            )
        else:
            records["qaoa"] = ConflictSolverRecord("qaoa", [], float("inf"), q.runtime, False, False, f"failed: {q.error}")

    sa = solve_sa(qubo, num_reads=100, num_sweeps=1000, seed=seed)
    if sa.status == "success":
        records["sa"] = record("sa", sa.best_x, sa.runtime_seconds, note="simulated annealing (dwave-neal)")
    else:
        records["sa"] = ConflictSolverRecord("sa", [], float("inf"), sa.runtime_seconds, False, False, f"failed: {sa.error}")

    g_order, g_rt = solve_conflict_greedy(reqs)
    records["greedy"] = record("greedy", _sequence_to_bits(g_order), g_rt, note="priority, then earliest arrival")

    valid = [r for r in records.values() if r.is_valid]
    if not valid:
        raise RuntimeError("No solver produced a valid emergency sequence.")
    best_e = min(r.energy for r in valid)
    best = [r for r in valid if abs(r.energy - best_e) < 1e-6]
    winner = min(best, key=lambda r: r.runtime_seconds).solver_name
    if len(best) == len(valid):
        verdict = f"All valid solvers reached the same energy ({best_e:.2f}); this instance does not separate them."
    else:
        losers = sorted(r.solver_name for r in valid if r not in best)
        verdict = (
            f"{' / '.join(sorted(r.solver_name for r in best))} reached the best energy ({best_e:.2f}); "
            f"{', '.join(losers)} did worse on this instance."
        )
    if "qaoa" in records and not records["qaoa"].is_valid:
        verdict += " QAOA returned an invalid sequence."
    elif "qaoa" in records and records["qaoa"] not in best:
        verdict += " QAOA lost this instance."
    return ConflictArbiterResult(
        conflict_intersection=conflict_intersection,
        num_qubits=K * K,
        records=records,
        exact_energy=float(exact_e),
        winner=winner,
        verdict=verdict,
    )


def solve_emergency_conflict(
    requests: Sequence[EmergencyConflictRequest],
    conflict_intersection: str,
    current_time: int,
    clearance_time_seconds: int = 6,
    solver: str = "sa",
    seed: int = 42,
) -> EmergencyConflictSchedule:
    """Solve the emergency conflict QUBO ('sa' default, 'qaoa', 'greedy' or 'exact')."""
    if len(requests) <= 1:
        vehs = [r.vehicle_id for r in requests]
        intervals = {r.vehicle_id: (current_time, current_time + clearance_time_seconds) for r in requests}
        return EmergencyConflictSchedule(
            conflict_intersection=conflict_intersection,
            sequenced_vehicles=vehs,
            clearance_intervals=intervals,
            solver_used="direct",
            qubo_energy=0.0,
            is_feasible=True,
        )

    if solver not in ("sa", "qaoa", "greedy", "exact"):
        raise ValueError(f"Unknown conflict solver '{solver}'. Use 'sa', 'qaoa', 'greedy' or 'exact'.")

    reqs = list(requests)
    K = len(reqs)
    qubo = build_conflict_qubo(reqs, conflict_intersection, clearance_time_seconds=clearance_time_seconds)
    order: Optional[List[int]] = None
    solver_used = solver

    if solver == "greedy":
        order, _ = solve_conflict_greedy(reqs)
        solver_used = "greedy_conflict"
    elif solver == "exact":
        order, _, _ = solve_conflict_exact(qubo, K)
        solver_used = "exact_conflict"
    elif solver == "qaoa" and K <= 4:
        from optimization.qaoa_solver import solve_tiny_qaoa

        q = solve_tiny_qaoa(qubo, p=2, maxiter=60, shots=2048, seed=seed)
        order = decode_conflict_sequence(q.best_x, K) if q.status == "success" else None
        solver_used = "qaoa_conflict_qubo"

    if order is None and solver in ("sa", "qaoa"):
        sa_res = solve_sa(qubo, num_reads=50, num_sweeps=500, seed=seed)
        order = decode_conflict_sequence(sa_res.best_x, K) if sa_res.status == "success" else None
        solver_used = "sa_conflict_qubo" if solver == "sa" else "sa_fallback"
    if order is None:
        order, _ = solve_conflict_greedy(reqs)  # deterministic last resort so the schedule is always safe
        solver_used = "rule_based"

    energy = float(qubo.energy(_sequence_to_bits(order)))
    ordered_ids = [reqs[e].vehicle_id for e in order]

    # Non-overlapping green intervals
    intervals: Dict[str, Tuple[int, int]] = {}
    curr_t = current_time
    for vid in ordered_ids:
        intervals[vid] = (curr_t, curr_t + clearance_time_seconds)
        curr_t += clearance_time_seconds + 1  # 1 second buffer

    return EmergencyConflictSchedule(
        conflict_intersection=conflict_intersection,
        sequenced_vehicles=ordered_ids,
        clearance_intervals=intervals,
        solver_used=solver_used,
        qubo_energy=energy,
        is_feasible=True,
    )


def requests_from_configs(
    configs: Sequence[Any],
    conflict_intersection: str,
    seconds_per_hop: int = 3,
) -> List[EmergencyConflictRequest]:
    """Build conflict requests for every configured ambulance whose route crosses ``conflict_intersection``.

    ``configs`` are duck-typed (vehicle_id, arrival_time, route, priority) - e.g. ``EmergencyVehicleConfig``.
    Arrival at the junction is the spawn time plus ``seconds_per_hop`` per junction along the route.
    """
    out: List[EmergencyConflictRequest] = []
    for cfg in configs:
        if conflict_intersection not in cfg.route:
            continue
        hops = cfg.route.index(conflict_intersection)
        out.append(
            EmergencyConflictRequest(
                vehicle_id=cfg.vehicle_id,
                route=tuple(cfg.route),
                current_intersection=cfg.route[0],
                distance_to_conflict=hops,
                estimated_arrival_at_conflict=int(cfg.arrival_time + hops * seconds_per_hop),
                priority_level=int(cfg.priority),
            )
        )
    return out
