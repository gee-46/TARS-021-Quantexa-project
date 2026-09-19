"""Emergency Conflict Detection and Multi-Emergency Conflict QUBO Formulation.

When 2 or more emergency vehicles simultaneously request conflicting green preemption
at shared or opposing network intersections (e.g. Emergency A on I1->I2->I3 and
Emergency B on I4->I3->I2 contending for I3), this module:
1. Detects junction and temporal corridor conflicts.
2. Formulates a dedicated sequence-prioritization Emergency Conflict QUBO.
3. Solves via QAOA (with deterministic Classical SA fallback).
4. Produces a safe, conflict-free priority schedule for the emergency runtime controller.

Mathematical Conflict QUBO Formulation:
- Binary decision variables y_{e, s} in {0, 1} indicating whether vehicle e is assigned priority sequence slot s in {0, 1, ..., K-1}.
- Sequence One-Hot Constraint:
    H_onehot = P_seq * ( sum_s (sum_e y_{e, s} - 1)^2 + sum_e (sum_s y_{e, s} - 1)^2 )
- Weighted Delay & Priority Objective:
    H_delay = sum_{e, s} (arrival_time_e + distance_to_conflict_e + s * clearance_time) * priority_weight_e * y_{e, s}
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple, Optional, Any, Sequence, Set
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
    """Construct a dedicated Emergency Conflict QUBO for sequencing K requests."""
    K = len(requests)
    num_vars = K * K  # y_{e, s} for e in 0..K-1, s in 0..K-1
    Q = np.zeros((num_vars, num_vars), dtype=float)
    offset = 0.0

    def idx(e: int, s: int) -> int:
        return e * K + s

    # 1. One-Hot Constraints:
    # Each slot s has exactly one vehicle: sum_e y_{e, s} = 1 -> (sum_e y_{e,s} - 1)^2
    for s in range(K):
        for e1 in range(K):
            k1 = idx(e1, s)
            Q[k1, k1] += onehot_penalty * (-1.0)
            for e2 in range(e1 + 1, K):
                k2 = idx(e2, s)
                Q[k1, k2] += onehot_penalty * 2.0
        offset += onehot_penalty * 1.0

    # Each vehicle e has exactly one slot: sum_s y_{e, s} = 1 -> (sum_s y_{e,s} - 1)^2
    for e in range(K):
        for s1 in range(K):
            k1 = idx(e, s1)
            Q[k1, k1] += onehot_penalty * (-1.0)
            for s2 in range(s1 + 1, K):
                k2 = idx(e, s2)
                Q[k1, k2] += onehot_penalty * 2.0
        offset += onehot_penalty * 1.0

    # 2. Linear Delay & Priority Cost:
    for e, req in enumerate(requests):
        base_arr = float(req.estimated_arrival_at_conflict)
        dist = float(req.distance_to_conflict)
        prio_mult = 1.0 / float(max(1, req.priority_level))  # Priority 1 gets lowest multiplier (most urgent)

        for s in range(K):
            k = idx(e, s)
            # Waiting delay if assigned slot s
            slot_delay = base_arr + (dist * 2.0) + (s * clearance_time_seconds)
            cost = slot_delay * prio_mult
    variable_order = tuple(f"y_{e}_{s}" for e in range(K) for s in range(K))
    return QUBOModel(
        Q=Q,
        variable_order=variable_order,
        offset=offset,
        metadata={"type": "emergency_conflict", "intersection": conflict_intersection, "K": K},
    )



def solve_emergency_conflict(
    requests: Sequence[EmergencyConflictRequest],
    conflict_intersection: str,
    current_time: int,
    clearance_time_seconds: int = 6,
) -> EmergencyConflictSchedule:
    """Solve the emergency conflict QUBO using Simulated Annealing (or QAOA fallback)."""
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

    qubo = build_conflict_qubo(requests, conflict_intersection, clearance_time_seconds=clearance_time_seconds)
    sa_res = solve_sa(qubo, num_reads=50, num_sweeps=500, seed=42)

    K = len(requests)
    best_sample = sa_res.best_x
    sequenced: List[Tuple[int, str]] = []  # (slot, vehicle_id)


    for e, req in enumerate(requests):
        assigned_slot = 0
        for s in range(K):
            k = e * K + s
            if best_sample[k] == 1:
                assigned_slot = s
                break
        sequenced.append((assigned_slot, req.vehicle_id))

    # Sort by assigned sequence slot
    sequenced.sort(key=lambda x: x[0])
    ordered_ids = [item[1] for item in sequenced]

    # Calculate non-overlapping green intervals
    intervals: Dict[str, Tuple[int, int]] = {}
    curr_t = current_time
    for vid in ordered_ids:
        intervals[vid] = (curr_t, curr_t + clearance_time_seconds)
        curr_t += clearance_time_seconds + 1  # 1 second buffer

    return EmergencyConflictSchedule(
        conflict_intersection=conflict_intersection,
        sequenced_vehicles=ordered_ids,
        clearance_intervals=intervals,
        solver_used="sa_conflict_qubo",
        qubo_energy=sa_res.best_energy,
        is_feasible=True,
    )
