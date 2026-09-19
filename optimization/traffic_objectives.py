"""Local Traffic Objective Components Formulation and Validation.

Implements the three local intersection objective terms:
1. Waiting Penalty (H_wait):
       H_wait = B * sum_{i, t} (q_i / t) * x_{i, t}
2. Capacity Overflow Penalty (H_capacity):
       H_capacity = C * sum_{i, t} max(0, d_i - threshold) * (45 - t) * x_{i, t}
3. Throughput Reward (H_throughput):
       H_throughput = E * sum_{i, t} min(q_i, mu * t) * x_{i, t}

In the global MINIMIZATION objective:
       H_local = H_wait + H_capacity - H_throughput

Matrix Representation Properties:
- All three traffic terms are strictly LINEAR in x_{i, t} (since x^2 = x for x in {0, 1}).
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
    """

    wait_weight: float = 2.0  # B
    capacity_weight: float = 10.0  # C
    capacity_threshold: float = 0.7
    throughput_weight: float = 1.0  # E
    service_rate: float = 1.0  # mu


@dataclass(frozen=True)
class TrafficState:
    """Lightweight decoupled snapshot of the traffic network state.

    Attributes:
        queues: Map of intersection ID to pending queue count q_i >= 0.
        densities: Map of intersection ID to density/demand ratio d_i in [0, 1+].
        capacities: Optional map of intersection ID to vehicle capacity C_i.
    """

    queues: Dict[str, float]
    densities: Dict[str, float]
    capacities: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrafficState":
        """Parse raw dictionary input from external simulator or mock state.

        Supported structure:
            {
                "I1": {"queue": 20, "density": 0.65, "capacity": 40},
                "I2": {"queue": 8, "density": 0.30, "capacity": 35},
                ...
            }
        """
        queues: Dict[str, float] = {}
        densities: Dict[str, float] = {}
        capacities: Dict[str, float] = {}

        for inter in INTERSECTIONS:
            inter_data = data.get(inter, {})
            if isinstance(inter_data, dict):
                queues[inter] = float(inter_data.get("queue", 0.0))
                densities[inter] = float(inter_data.get("density", 0.0))
                if "capacity" in inter_data:
                    capacities[inter] = float(inter_data["capacity"])
            else:
                # Direct scalar fallback if provided
                queues[inter] = float(inter_data) if inter_data else 0.0
                densities[inter] = 0.0

        return cls(queues=queues, densities=densities, capacities=capacities)


def add_wait_term(
    Q: np.ndarray,
    traffic_state: Union[TrafficState, Dict[str, Any]],
    config: TrafficObjectiveConfig = TrafficObjectiveConfig(),
) -> np.ndarray:
    """Add H_wait linear penalty contributions to matrix Q diagonal.

    Formula:
        For variable k = (i, t):
            Q[k, k] += B * (q_i / t)
    """
    state = traffic_state if isinstance(traffic_state, TrafficState) else TrafficState.from_dict(traffic_state)
    B = config.wait_weight

    for inter in INTERSECTIONS:
        q_i = state.queues.get(inter, 0.0)
        for dur in DURATIONS:
            k = get_variable_index(inter, dur)
            coeff = B * (q_i / float(dur))
            Q[k, k] += coeff

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

    Throughput is a reward in a minimization problem, so its QUBO contribution is NEGATIVE:
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


def add_traffic_terms(
    Q: np.ndarray,
    traffic_state: Union[TrafficState, Dict[str, Any]],
    config: TrafficObjectiveConfig = TrafficObjectiveConfig(),
) -> np.ndarray:
    """Add all three local traffic objective terms (H_wait + H_capacity - H_throughput) to Q."""
    add_wait_term(Q, traffic_state, config)
    add_capacity_term(Q, traffic_state, config)
    add_throughput_term(Q, traffic_state, config)
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


def evaluate_local_traffic_qubo_energy(
    x: Sequence[int],
    traffic_state: Union[TrafficState, Dict[str, Any]],
    config: TrafficObjectiveConfig = TrafficObjectiveConfig(),
) -> float:
    """Direct mathematical evaluation of the net local traffic QUBO energy:

    E_local(x) = H_wait(x) + H_capacity(x) - H_throughput(x)
    """
    w = evaluate_wait(x, traffic_state, config)
    c = evaluate_capacity(x, traffic_state, config)
    t = evaluate_throughput(x, traffic_state, config)
    return float(w + c - t)
