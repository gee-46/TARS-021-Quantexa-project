"""Inter-Intersection Coupling Term Formulation and Validation.

Implements the network-level inter-intersection coupling penalty:
    H_coupling = D * sum_{(i -> j) in edges} sum_{t_i} sum_{t_j}
                 (t_i / 45) * (q_j / C_j) * (1 - t_j / 45) * x_{i, t_i} * x_{j, t_j}

Mathematical Properties:
- Directional: Edge i -> j depends on downstream intersection j's congestion (q_j / C_j).
- Spillback Penalty: Penalizes giving high green time to upstream i (t_i / 45) when downstream j
  is congested (q_j / C_j) and has insufficient green time (1 - t_j / 45).
- Pairwise Quadratic: Produces strictly off-diagonal upper-triangular entries Q[min(a,b), max(a,b)].
- Zero for t_j = 45: Because (1 - 45/45) = 0, any duration choice where downstream t_j = 45s
  has an exact 0.0 coupling penalty.
- No Diagonal Terms: Since i != j, a != b, no diagonal entries are created.
- No Constant Offset: Contributes exactly 0.0 to QUBO offset.
"""

from dataclasses import dataclass
from typing import Sequence, Tuple, Dict, Any, Union, List
import numpy as np

from optimization.variables import (
    INTERSECTIONS,
    DURATIONS,
    NUM_VARIABLES,
    VARIABLE_INDEX,
    INDEX_TO_VARIABLE,
    get_variable_index,
)
from optimization.traffic_objectives import TrafficState
from optimization.qubo_model import QUBOModel, qubo_energy

# Default capacity when not explicitly specified
DEFAULT_INTERSECTION_CAPACITY: float = 40.0


@dataclass(frozen=True)
class CouplingConfig:
    """Hyperparameters for inter-intersection coupling term.

    Attributes:
        coupling_weight: Multiplier D for spillback penalty (default 5.0).
        default_capacity: Fallback capacity C_j if not in TrafficState (default 40.0).
    """

    coupling_weight: float = 5.0  # D
    default_capacity: float = DEFAULT_INTERSECTION_CAPACITY


def validate_coupling_inputs(
    edges: Sequence[Tuple[str, str]],
    traffic_state: Union[TrafficState, Dict[str, Any]],
    default_capacity: float = DEFAULT_INTERSECTION_CAPACITY,
) -> Tuple[List[Tuple[str, str]], TrafficState]:
    """Validate graph edges and downstream traffic state for mathematical consistency.

    Args:
        edges: Sequence of directed edge tuples (source, target).
        traffic_state: TrafficState object or raw state dictionary.
        default_capacity: Fallback capacity if capacity map lacks an entry.

    Returns:
        Tuple[List[Tuple[str, str]], TrafficState]: Validated edges and TrafficState.

    Raises:
        ValueError: If self-loops, negative queues, zero/negative capacities, or unknown intersections exist.
    """
    state = traffic_state if isinstance(traffic_state, TrafficState) else TrafficState.from_dict(traffic_state)
    validated_edges: List[Tuple[str, str]] = []

    # Validate traffic state parameters
    for inter in INTERSECTIONS:
        q = state.queues.get(inter, 0.0)
        if q < 0.0:
            raise ValueError(
                f"Negative queue detected at intersection '{inter}': {q}. Queues must be non-negative."
            )
        c = state.capacities.get(inter, default_capacity)
        if c <= 0.0:
            raise ValueError(
                f"Non-positive capacity detected at intersection '{inter}': {c}. Downstream capacity C_j must be > 0."
            )

    # Validate edge structure
    for edge in edges:
        if len(edge) != 2:
            raise ValueError(f"Invalid edge specification '{edge}'. Expected 2-tuple (source, target).")
        src, dst = edge
        if src not in INTERSECTIONS:
            raise ValueError(
                f"Unknown source intersection '{src}' in edge {edge}. Expected one of {INTERSECTIONS}."
            )
        if dst not in INTERSECTIONS:
            raise ValueError(
                f"Unknown destination intersection '{dst}' in edge {edge}. Expected one of {INTERSECTIONS}."
            )
        if src == dst:
            raise ValueError(
                f"Self-loop edge ('{src}', '{dst}') is forbidden. Inter-intersection coupling requires src != dst."
            )
        validated_edges.append((src, dst))

    return validated_edges, state


def add_coupling_term(
    Q: np.ndarray,
    edges: Sequence[Tuple[str, str]],
    traffic_state: Union[TrafficState, Dict[str, Any]],
    config: CouplingConfig = CouplingConfig(),
) -> np.ndarray:
    """Add H_coupling pairwise quadratic penalty contributions to matrix Q.

    Strictly adheres to the Upper-Triangular Convention:
        Q[min(a, b), max(a, b)] += coefficient

    Args:
        Q: 2D numpy array of shape (NUM_VARIABLES, NUM_VARIABLES), upper-triangular.
        edges: Sequence of directed edges [(src, dst), ...].
        traffic_state: TrafficState or dictionary.
        config: CouplingConfig with coupling_weight D.

    Returns:
        np.ndarray: Modified upper-triangular matrix Q.
    """
    if Q.shape != (NUM_VARIABLES, NUM_VARIABLES):
        raise ValueError(
            f"Matrix Q must have shape ({NUM_VARIABLES}, {NUM_VARIABLES}), got {Q.shape}."
        )

    valid_edges, state = validate_coupling_inputs(
        edges=edges,
        traffic_state=traffic_state,
        default_capacity=config.default_capacity,
    )
    D = config.coupling_weight

    for src, dst in valid_edges:
        q_dst = state.queues.get(dst, 0.0)
        c_dst = state.capacities.get(dst, config.default_capacity)
        density_factor = q_dst / c_dst

        for t_src in DURATIONS:
            idx_src = get_variable_index(src, t_src)
            src_factor = float(t_src) / 45.0

            for t_dst in DURATIONS:
                idx_dst = get_variable_index(dst, t_dst)
                dst_factor = 1.0 - (float(t_dst) / 45.0)

                # Pairwise penalty coefficient
                coeff = D * src_factor * density_factor * dst_factor

                if not np.isclose(coeff, 0.0):
                    # Store strictly once at upper-triangular position min(a, b), max(a, b)
                    row = min(idx_src, idx_dst)
                    col = max(idx_src, idx_dst)
                    if row == col:
                        raise ValueError(
                            f"Internal error: coupling mapped to diagonal position ({row}, {col})."
                        )
                    Q[row, col] += coeff

    return Q


def evaluate_coupling(
    x: Sequence[int],
    edges: Sequence[Tuple[str, str]],
    traffic_state: Union[TrafficState, Dict[str, Any]],
    config: CouplingConfig = CouplingConfig(),
) -> float:
    """Direct mathematical evaluation of the coupling penalty H_coupling(x).

    Formula:
        H_coupling(x) = D * sum_{(i->j) in edges} sum_{t_i, t_j}
                        (t_i / 45) * (q_j / C_j) * (1 - t_j / 45) * x_{i, t_i} * x_{j, t_j}

    Args:
        x: Binary state vector of length NUM_VARIABLES (12).
        edges: Directed edge list.
        traffic_state: TrafficState or dict.
        config: CouplingConfig.

    Returns:
        float: Exact evaluated coupling energy.
    """
    x_vec = np.asarray(x, dtype=np.float64)
    if len(x_vec) != NUM_VARIABLES:
        raise ValueError(f"State vector x must have length {NUM_VARIABLES}, got {len(x_vec)}.")

    valid_edges, state = validate_coupling_inputs(
        edges=edges,
        traffic_state=traffic_state,
        default_capacity=config.default_capacity,
    )
    D = config.coupling_weight
    total_energy = 0.0

    for src, dst in valid_edges:
        q_dst = state.queues.get(dst, 0.0)
        c_dst = state.capacities.get(dst, config.default_capacity)
        density_factor = q_dst / c_dst

        for t_src in DURATIONS:
            idx_src = get_variable_index(src, t_src)
            src_factor = float(t_src) / 45.0

            for t_dst in DURATIONS:
                idx_dst = get_variable_index(dst, t_dst)
                dst_factor = 1.0 - (float(t_dst) / 45.0)

                coeff = D * src_factor * density_factor * dst_factor
                total_energy += coeff * x_vec[idx_src] * x_vec[idx_dst]

    return float(total_energy)
