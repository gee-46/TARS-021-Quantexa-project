"""Local Traffic Objective Components Formulation and Validation.

Implements local intersection objective terms:
1. Waiting Penalty (H_wait):
       H_wait = B * sum_{i, t} (q_i / t) * x_{i, t}
   Optionally person-weighted if person_weighted=True.
2. Capacity Overflow Penalty (H_capacity):
       H_capacity = C * sum_{i, t} max(0, d_i - threshold) * (45 - t) * x_{i, t}
3. Throughput Reward (H_throughput):
       H_throughput = E * sum_{i, t} min(q_i, mu * t) * x_{i, t}
4. Starvation & Fairness Penalty (H_fairness / H_starvation):
       Penalizes under-allocating green time to starved approaches.

Matrix Representation Properties:
- All traffic terms are strictly LINEAR in x_{i, t} (since x^2 = x for x in {0, 1}).
- They modify ONLY diagonal entries Q[k, k].
- Off-diagonal interaction entries remain strictly 0.0.
- Constant energy offset contribution is exactly 0.0.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Sequence, Tuple, Union, Optional
import numpy as np

from optimization.variables import (
    INTERSECTIONS,
    DURATIONS,
    NUM_VARIABLES,
    VARIABLE_INDEX,
    INDEX_TO_VARIABLE,
    get_variable_index,
    get_intersection_variable_indices,
)
from optimization.qubo_model import QUBOModel, qubo_energy


@dataclass(frozen=True)
class TrafficObjectiveConfig:
    """Configuration hyperparameters for traffic objective terms.

    Attributes:
        wait_weight: Weight coefficient B for queue waiting penalty.
        capacity_weight: Weight coefficient C for capacity threshold penalty.
        capacity_threshold: Critical density threshold (default 0.7).
        throughput_weight: Weight coefficient E for throughput service reward.
        service_rate: Flow saturation service rate parameter mu (vehicles/second).
        person_weighted: If True, uses person-weighted queue counts for H_wait.
        fairness_weight: Weight coefficient for Jain fairness / delay equity balancing.
        starvation_penalty_weight: Weight coefficient for approaches exceeding max_wait_cap.
        max_wait_cap: Maximum acceptable approach delay in seconds before starvation penalty activates.
        cross_street_weight: Weight for cross-street delay (0.0 = off, the default). Treats each cross street like an approach
            whose queue is one cycle of arrivals waiting for its share of the cycle: X * (lambda_cross * C) / (C - t).
        cycle_length: Signal cycle length C in seconds (used by the cross-street term).
    """

    wait_weight: float = 2.0  # B
    capacity_weight: float = 10.0  # C
    capacity_threshold: float = 0.7
    throughput_weight: float = 1.0  # E
    service_rate: float = 1.0  # mu
    person_weighted: bool = False
    fairness_weight: float = 0.0
    starvation_penalty_weight: float = 0.0
    max_wait_cap: float = 120.0
    cross_street_weight: float = 0.0
    cycle_length: float = 60.0


@dataclass(frozen=True)
class TrafficState:
    """Lightweight decoupled snapshot of the traffic network state.

    Attributes:
        queues: Map of intersection ID to pending vehicle queue count q_i >= 0.
        densities: Map of intersection ID to density/demand ratio d_i in [0, 1+].
        capacities: Optional map of intersection ID to vehicle capacity C_i.
        person_queues: Optional map of intersection ID to total pending passenger count.
        approach_waiting_times: Optional map of intersection ID to maximum approach wait time.
        cross_rates: Optional map of intersection ID to cross-street arrival rate (vehicles/second).
    """

    queues: Dict[str, float]
    densities: Dict[str, float]
    capacities: Dict[str, float] = field(default_factory=dict)
    person_queues: Dict[str, float] = field(default_factory=dict)
    approach_waiting_times: Dict[str, float] = field(default_factory=dict)
    cross_rates: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrafficState":
        """Parse raw dictionary input from external simulator or mock state."""
        queues: Dict[str, float] = {}
        densities: Dict[str, float] = {}
        capacities: Dict[str, float] = {}
        person_queues: Dict[str, float] = {}
        approach_waiting_times: Dict[str, float] = {}
        cross_rates: Dict[str, float] = {}

        for inter in INTERSECTIONS:
            inter_data = data.get(inter, {})
            if isinstance(inter_data, dict):
                queues[inter] = float(inter_data.get("queue", 0.0))
                densities[inter] = float(inter_data.get("density", 0.0))
                if "capacity" in inter_data:
                    capacities[inter] = float(inter_data["capacity"])
                if "person_queue" in inter_data:
                    person_queues[inter] = float(inter_data["person_queue"])
                if "max_wait" in inter_data:
                    approach_waiting_times[inter] = float(inter_data["max_wait"])
                if "cross_rate" in inter_data:
                    cross_rates[inter] = float(inter_data["cross_rate"])
            else:
                queues[inter] = float(inter_data) if inter_data else 0.0
                densities[inter] = 0.0

        return cls(
            queues=queues,
            densities=densities,
            capacities=capacities,
            person_queues=person_queues,
            approach_waiting_times=approach_waiting_times,
            cross_rates=cross_rates,
        )


def calculate_jain_fairness_index(values: Sequence[float]) -> float:
    """Calculate Jain's Fairness Index across a sequence of approach metrics (e.g. wait times or service rates).

    Formula:
        J(x_1, ..., x_n) = (sum(x_i))^2 / (n * sum(x_i^2))

    Properties:
        - Bounded in [1/n, 1.0]
        - 1.0 indicates perfectly equal distribution.
        - If all inputs are zero, returns 1.0 (trivially fair).
    """
    if not values:
        return 1.0
    arr = np.array([max(0.0, float(v)) for v in values])
    n = len(arr)
    sum_x = np.sum(arr)
    sum_sq = np.sum(arr**2)

    if sum_sq == 0.0:
        return 1.0

    jain = float((sum_x**2) / (n * sum_sq))
    return min(1.0, max(1.0 / n, jain))


def add_wait_term(
    Q: np.ndarray,
    traffic_state: Union[TrafficState, Dict[str, Any]],
    config: TrafficObjectiveConfig = TrafficObjectiveConfig(),
) -> np.ndarray:
    """Add H_wait linear penalty contributions to matrix Q diagonal.

    Formula:
        For variable k = (i, t):
            Q[k, k] += B * (q_eff_i / t)
    """
    state = traffic_state if isinstance(traffic_state, TrafficState) else TrafficState.from_dict(traffic_state)
    B = config.wait_weight

    for inter in INTERSECTIONS:
        if config.person_weighted and state.person_queues:
            q_i = state.person_queues.get(inter, state.queues.get(inter, 0.0))
        else:
            q_i = state.queues.get(inter, 0.0)

        for dur in DURATIONS:
            k = get_variable_index(inter, dur)
            coeff = B * (q_i / float(dur))
            Q[k, k] += coeff

    return Q


def add_cross_street_term(
    Q: np.ndarray,
    traffic_state: Union[TrafficState, Dict[str, Any]],
    config: TrafficObjectiveConfig = TrafficObjectiveConfig(),
) -> np.ndarray:
    """Add the cross-street delay penalty: a longer arterial green leaves the cross street less of the cycle.

    Formula (mirrors H_wait, whose form is B * q / t for the arterial approach):
        For variable k = (i, t):
            Q[k, k] += X * (lambda_cross_i * C) / (C - t)
    where lambda_cross_i is the cross-street arrival rate at junction i (vehicles/s), C the cycle length, and
    lambda_cross_i * C the vehicles that accumulate over one cycle. Off when X = 0 or no cross rates are given.
    """
    state = traffic_state if isinstance(traffic_state, TrafficState) else TrafficState.from_dict(traffic_state)
    X = config.cross_street_weight
    if X <= 0.0 or not state.cross_rates:
        return Q
    C = float(config.cycle_length)
    for inter in INTERSECTIONS:
        lam = state.cross_rates.get(inter, 0.0)
        if lam <= 0.0:
            continue
        for dur in DURATIONS:
            k = get_variable_index(inter, dur)
            Q[k, k] += X * (lam * C) / (C - float(dur))
    return Q


def add_capacity_term(
    Q: np.ndarray,
    traffic_state: Union[TrafficState, Dict[str, Any]],
    config: TrafficObjectiveConfig = TrafficObjectiveConfig(),
) -> np.ndarray:
    """Add H_capacity linear penalty contributions to matrix Q diagonal.

    Formula:
        For variable k = (i, t):
            Q[k, k] += C * max(0, d_i - threshold) * (45 - t)
    """
    state = traffic_state if isinstance(traffic_state, TrafficState) else TrafficState.from_dict(traffic_state)
    C = config.capacity_weight
    thresh = config.capacity_threshold

    for inter in INTERSECTIONS:
        d_i = state.densities.get(inter, 0.0)
        excess = max(0.0, d_i - thresh)
        for dur in DURATIONS:
            k = get_variable_index(inter, dur)
            coeff = C * excess * (45.0 - float(dur))
            Q[k, k] += coeff

    return Q


def add_throughput_term(
    Q: np.ndarray,
    traffic_state: Union[TrafficState, Dict[str, Any]],
    config: TrafficObjectiveConfig = TrafficObjectiveConfig(),
) -> np.ndarray:
    """Add -H_throughput linear reward contributions to matrix Q diagonal.

    Formula:
        For variable k = (i, t):
            Q[k, k] += -E * min(q_i, mu * t)
    """
    state = traffic_state if isinstance(traffic_state, TrafficState) else TrafficState.from_dict(traffic_state)
    E = config.throughput_weight
    mu = config.service_rate

    for inter in INTERSECTIONS:
        q_i = state.queues.get(inter, 0.0)
        for dur in DURATIONS:
            k = get_variable_index(inter, dur)
            served = min(float(q_i), mu * float(dur))
            reward = E * served
            Q[k, k] += -reward

    return Q


def add_starvation_fairness_term(
    Q: np.ndarray,
    traffic_state: Union[TrafficState, Dict[str, Any]],
    config: TrafficObjectiveConfig = TrafficObjectiveConfig(),
) -> np.ndarray:
    """Add starvation penalty and fairness balancing contributions to matrix Q diagonal.

    Penalizes choosing shorter green durations (15s, 30s) when an approach is starving.
    """
    state = traffic_state if isinstance(traffic_state, TrafficState) else TrafficState.from_dict(traffic_state)
    starv_w = config.starvation_penalty_weight
    fair_w = config.fairness_weight
    cap = config.max_wait_cap

    if starv_w <= 0.0 and fair_w <= 0.0:
        return Q

    total_wait = sum(state.approach_waiting_times.values()) if state.approach_waiting_times else 0.0

    for inter in INTERSECTIONS:
        w_i = state.approach_waiting_times.get(inter, 0.0)
        starv_excess = max(0.0, w_i - cap)

        for dur in DURATIONS:
            k = get_variable_index(inter, dur)
            shortage = 45.0 - float(dur)

            # Starvation penalty for exceeding threshold
            if starv_w > 0.0 and starv_excess > 0.0:
                Q[k, k] += starv_w * (starv_excess / cap) * shortage

            # General fairness term proportional to approach wait share
            if fair_w > 0.0 and total_wait > 0.0:
                wait_share = w_i / total_wait
                Q[k, k] += fair_w * wait_share * shortage

    return Q


def add_traffic_terms(
    Q: np.ndarray,
    traffic_state: Union[TrafficState, Dict[str, Any]],
    config: TrafficObjectiveConfig = TrafficObjectiveConfig(),
) -> np.ndarray:
    """Apply all local traffic objective terms to the upper-triangular QUBO matrix Q."""
    Q = add_wait_term(Q, traffic_state, config)
    Q = add_capacity_term(Q, traffic_state, config)
    Q = add_throughput_term(Q, traffic_state, config)
    Q = add_starvation_fairness_term(Q, traffic_state, config)
    Q = add_cross_street_term(Q, traffic_state, config)
    return Q


# ----------------------------------------------------------------------
# Direct Component Evaluators
# ----------------------------------------------------------------------

def evaluate_wait(
    x: Sequence[int],
    traffic_state: Union[TrafficState, Dict[str, Any]],
    config: TrafficObjectiveConfig = TrafficObjectiveConfig(),
) -> float:
    """Direct mathematical evaluation of waiting penalty H_wait(x)."""
    state = traffic_state if isinstance(traffic_state, TrafficState) else TrafficState.from_dict(traffic_state)
    x_vec = np.asarray(x, dtype=np.float64)
    B = config.wait_weight
    total = 0.0

    for inter in INTERSECTIONS:
        if config.person_weighted and state.person_queues:
            q_i = state.person_queues.get(inter, state.queues.get(inter, 0.0))
        else:
            q_i = state.queues.get(inter, 0.0)

        for dur in DURATIONS:
            k = get_variable_index(inter, dur)
            total += B * (q_i / float(dur)) * x_vec[k]

    return float(total)


def evaluate_capacity(
    x: Sequence[int],
    traffic_state: Union[TrafficState, Dict[str, Any]],
    config: TrafficObjectiveConfig = TrafficObjectiveConfig(),
) -> float:
    """Direct mathematical evaluation of capacity penalty H_capacity(x)."""
    state = traffic_state if isinstance(traffic_state, TrafficState) else TrafficState.from_dict(traffic_state)
    x_vec = np.asarray(x, dtype=np.float64)
    C = config.capacity_weight
    thresh = config.capacity_threshold
    total = 0.0

    for inter in INTERSECTIONS:
        d_i = state.densities.get(inter, 0.0)
        excess = max(0.0, d_i - thresh)
        for dur in DURATIONS:
            k = get_variable_index(inter, dur)
            total += C * excess * (45.0 - float(dur)) * x_vec[k]

    return float(total)


def evaluate_throughput(
    x: Sequence[int],
    traffic_state: Union[TrafficState, Dict[str, Any]],
    config: TrafficObjectiveConfig = TrafficObjectiveConfig(),
) -> float:
    """Direct mathematical evaluation of throughput service reward H_throughput(x).

    Note: Returns the positive reward value.
    """
    state = traffic_state if isinstance(traffic_state, TrafficState) else TrafficState.from_dict(traffic_state)
    x_vec = np.asarray(x, dtype=np.float64)
    E = config.throughput_weight
    mu = config.service_rate
    total = 0.0

    for inter in INTERSECTIONS:
        q_i = state.queues.get(inter, 0.0)
        for dur in DURATIONS:
            k = get_variable_index(inter, dur)
            served = min(float(q_i), mu * float(dur))
            total += E * served * x_vec[k]

    return float(total)


def evaluate_starvation_fairness(
    x: Sequence[int],
    traffic_state: Union[TrafficState, Dict[str, Any]],
    config: TrafficObjectiveConfig = TrafficObjectiveConfig(),
) -> float:
    """Direct mathematical evaluation of starvation/fairness penalty term."""
    state = traffic_state if isinstance(traffic_state, TrafficState) else TrafficState.from_dict(traffic_state)
    x_vec = np.asarray(x, dtype=np.float64)
    starv_w = config.starvation_penalty_weight
    fair_w = config.fairness_weight
    cap = config.max_wait_cap

    if starv_w <= 0.0 and fair_w <= 0.0:
        return 0.0

    total_wait = sum(state.approach_waiting_times.values()) if state.approach_waiting_times else 0.0
    total = 0.0

    for inter in INTERSECTIONS:
        w_i = state.approach_waiting_times.get(inter, 0.0)
        starv_excess = max(0.0, w_i - cap)

        for dur in DURATIONS:
            k = get_variable_index(inter, dur)
            shortage = 45.0 - float(dur)

            if starv_w > 0.0 and starv_excess > 0.0:
                total += starv_w * (starv_excess / cap) * shortage * x_vec[k]

            if fair_w > 0.0 and total_wait > 0.0:
                wait_share = w_i / total_wait
                total += fair_w * wait_share * shortage * x_vec[k]

    return float(total)


def evaluate_local_traffic_qubo_energy(
    x: Sequence[int],
    traffic_state: Union[TrafficState, Dict[str, Any]],
    config: TrafficObjectiveConfig = TrafficObjectiveConfig(),
) -> float:
    """Direct mathematical evaluation of the net local traffic QUBO energy:

    E_local(x) = H_wait(x) + H_capacity(x) - H_throughput(x) + H_starvation_fairness(x)
    """
    w = evaluate_wait(x, traffic_state, config)
    c = evaluate_capacity(x, traffic_state, config)
    t = evaluate_throughput(x, traffic_state, config)
    sf = evaluate_starvation_fairness(x, traffic_state, config)
    return float(w + c - t + sf)


def build_traffic_qubo(
    traffic_state: Union[TrafficState, Dict[str, Any]],
    config: TrafficObjectiveConfig = TrafficObjectiveConfig(),
) -> QUBOModel:
    """Build a standalone 12-variable QUBO model containing strictly local traffic terms."""
    Q = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=float)
    Q = add_traffic_terms(Q, traffic_state, config)
    return QUBOModel(Q=Q, offset=0.0, metadata={"type": "local_traffic_only"})
