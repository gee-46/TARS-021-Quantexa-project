"""One-Hot Quadratic Penalty Formulation and Validation.

Enforces the exact one-hot constraint across all traffic intersections:
    sum_{t in {15, 30, 45}} x_{i, t} = 1  for each intersection i in {I1, I2, I3, I4}

Mathematical expansion for penalty A * (sum_t x_{i, t} - 1)^2:
    = A * ( sum_t x_{i, t}^2 + 2 sum_{t < t'} x_{i, t} x_{i, t'} - 2 sum_t x_{i, t} + 1 )
    = A * ( sum_t x_{i, t} + 2 sum_{t < t'} x_{i, t} x_{i, t'} - 2 sum_t x_{i, t} + 1 )  [since x^2 = x for x in {0, 1}]
    = A * ( 1 - sum_t x_{i, t} + 2 sum_{t < t'} x_{i, t} x_{i, t'} )

Resulting Upper-Triangular Matrix Contributions (for penalty coefficient A):
    - Diagonal: Q[k, k] += -A for each variable k in intersection i
    - Pairwise: Q[k, j] += 2A for each pair k < j in intersection i
    - Lower triangular: strictly 0.0
    - Constant Offset: offset += A per intersection (total 4A for 4 intersections)
"""

from typing import Sequence, Tuple, Dict, Any, List
import numpy as np

from optimization.variables import (
    INTERSECTIONS,
    NUM_VARIABLES,
    VARIABLE_INDEX,
    INDEX_TO_VARIABLE,
    get_intersection_variable_indices,
)
from optimization.qubo_model import QUBOModel, qubo_energy

# Default tunable penalty coefficient for one-hot constraint
DEFAULT_ONEHOT_PENALTY: float = 100.0


def evaluate_onehot_penalty(
    x: Sequence[int],
    penalty_coefficient: float = DEFAULT_ONEHOT_PENALTY,
    intersections: Sequence[str] = INTERSECTIONS,
) -> float:
    """Direct mathematical evaluation of the one-hot penalty H_onehot(x).

    Formula:
        H_onehot(x) = A * sum_{i in intersections} ( sum_{t} x_{i, t} - 1 )^2

    Args:
        x: Binary state vector of length NUM_VARIABLES (12).
        penalty_coefficient: Penalty multiplier A.
        intersections: Sequence of intersection identifiers to evaluate.

    Returns:
        float: Exact penalty value. Zero if and only if every intersection has exactly 1 active duration.
    """
    x_vec = np.asarray(x, dtype=np.float64)
    if len(x_vec) != NUM_VARIABLES:
        raise ValueError(
            f"State vector x must have length {NUM_VARIABLES}, got {len(x_vec)}."
        )

    total_penalty = 0.0
    for inter in intersections:
        indices = get_intersection_variable_indices(inter)
        active_count = float(np.sum(x_vec[indices]))
        total_penalty += penalty_coefficient * ((active_count - 1.0) ** 2)

    return float(total_penalty)


def add_onehot_penalty(
    Q: np.ndarray,
    offset: float,
    penalty_coefficient: float = DEFAULT_ONEHOT_PENALTY,
    intersections: Sequence[str] = INTERSECTIONS,
) -> Tuple[np.ndarray, float]:
    """Add the one-hot quadratic penalty contributions to matrix Q and offset.

    Modifies Q in-place adhering strictly to the upper-triangular convention.

    Args:
        Q: 2D numpy array of shape (NUM_VARIABLES, NUM_VARIABLES), upper-triangular.
        offset: Current scalar constant energy offset.
        penalty_coefficient: Penalty scaling multiplier A.
        intersections: Sequence of intersection identifiers to enforce.

    Returns:
        Tuple[np.ndarray, float]: Updated (Q, offset).
    """
    if Q.shape != (NUM_VARIABLES, NUM_VARIABLES):
        raise ValueError(
            f"Matrix Q must have shape ({NUM_VARIABLES}, {NUM_VARIABLES}), got {Q.shape}."
        )

    updated_offset = offset
    for inter in intersections:
        indices = get_intersection_variable_indices(inter)
        # 1. Diagonal contribution: Q[k, k] += -A
        for k in indices:
            Q[k, k] += -penalty_coefficient

        # 2. Pairwise interaction within the same intersection: Q[k, j] += 2A for k < j
        for i_idx, k in enumerate(indices):
            for j in indices[i_idx + 1:]:
                if k < j:
                    Q[k, j] += 2.0 * penalty_coefficient
                else:
                    Q[j, k] += 2.0 * penalty_coefficient

        # 3. Constant offset contribution: offset += A per intersection
        updated_offset += penalty_coefficient

    return Q, updated_offset


def build_onehot_qubo(
    penalty_coefficient: float = DEFAULT_ONEHOT_PENALTY,
    intersections: Sequence[str] = INTERSECTIONS,
) -> QUBOModel:
    """Build an isolated QUBOModel containing solely the one-hot constraint terms.

    Args:
        penalty_coefficient: Penalty coefficient A.
        intersections: Intersections to enforce.

    Returns:
        QUBOModel: Fully formed upper-triangular QUBO model for H_onehot.
    """
    Q = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
    offset = 0.0
    Q, offset = add_onehot_penalty(
        Q=Q,
        offset=offset,
        penalty_coefficient=penalty_coefficient,
        intersections=intersections,
    )

    canonical_var_order = tuple(
        INDEX_TO_VARIABLE[idx] for idx in range(NUM_VARIABLES)
    )

    metadata: Dict[str, Any] = {
        "term": "H_onehot",
        "penalty_coefficient": penalty_coefficient,
        "intersections": list(intersections),
        "offset_contribution": offset,
    }

    return QUBOModel(
        Q=Q,
        variable_order=canonical_var_order,
        offset=offset,
        metadata=metadata,
    )
