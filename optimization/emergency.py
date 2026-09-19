"""Emergency Vehicle Corridor Constraints Formulation and Validation.

Implements the emergency priority green corridor constraint term:
    H_emergency = F * sum_{k in route} (1 - x_{k, forced_duration})

Mathematical Expansion:
    H_emergency = F * |route| - F * sum_{k in route} x_{k, forced_duration}

Upper-Triangular Matrix Contributions (for penalty F):
- Diagonal: Q[idx, idx] += -F  for idx = VARIABLE_INDEX[(k, forced_duration)]
- Pairwise/Off-diagonal: strictly 0.0 (no interaction terms created)
- Constant Offset: offset += F * |route| (scalar energy baseline)

Key Properties:
- Vehicle-Agnostic: Optimizes purely for the resolved route and forced duration without needing
  domain knowledge of vehicle types or priority policies.
- Compliant States: If all route intersections select x_{k, forced_duration} = 1, the penalty is 0.0.
- Violating States: Each route intersection failing to activate the forced duration incurs +F penalty.
"""

from dataclasses import dataclass
from typing import Sequence, Tuple, Dict, Any, Union, Optional
import numpy as np

from optimization.variables import (
    INTERSECTIONS,
    DURATIONS,
    NUM_VARIABLES,
    VARIABLE_INDEX,
    INDEX_TO_VARIABLE,
    get_variable_index,
)
from optimization.qubo_model import QUBOModel, qubo_energy

DEFAULT_EMERGENCY_WEIGHT: float = 50.0
DEFAULT_FORCED_DURATION: int = 45


@dataclass(frozen=True)
class EmergencyConstraints:
    """Immutable representation of an active emergency routing constraint.

    Attributes:
        route: Ordered tuple of unique intersection IDs along the emergency corridor.
        forced_duration: Duration to enforce along the corridor (must be 15, 30, or 45).
        emergency_weight: Scaling penalty multiplier F for non-compliance.
    """

    route: Tuple[str, ...]
    forced_duration: int = DEFAULT_FORCED_DURATION
    emergency_weight: float = DEFAULT_EMERGENCY_WEIGHT

    def __init__(
        self,
        route: Sequence[str],
        forced_duration: int = DEFAULT_FORCED_DURATION,
        emergency_weight: float = DEFAULT_EMERGENCY_WEIGHT,
    ) -> None:
        """Construct and validate EmergencyConstraints."""
        if not route:
            raise ValueError("Emergency route must not be empty.")

        route_tuple = tuple(route)

        # Check for unknown intersections
        for inter in route_tuple:
            if inter not in INTERSECTIONS:
                raise ValueError(
                    f"Unknown intersection '{inter}' in emergency route. "
                    f"Expected one of canonical intersections: {INTERSECTIONS}."
                )

        # Check for duplicate intersections
        if len(set(route_tuple)) != len(route_tuple):
            duplicates = [inter for inter in route_tuple if route_tuple.count(inter) > 1]
            raise ValueError(
                f"Duplicate intersection(s) {set(duplicates)} in emergency route: {route_tuple}. "
                f"Emergency routes must consist of unique ordered intersections."
            )

        # Validate forced duration
        if not isinstance(forced_duration, int) or forced_duration not in DURATIONS:
            raise ValueError(
                f"Invalid forced duration {forced_duration}. "
                f"Must be one of supported discrete durations: {DURATIONS}."
            )

        # Validate weight
        if emergency_weight <= 0.0:
            raise ValueError(
                f"Emergency weight F must be positive, got {emergency_weight}."
            )

        object.__setattr__(self, "route", route_tuple)
        object.__setattr__(self, "forced_duration", int(forced_duration))
        object.__setattr__(self, "emergency_weight", float(emergency_weight))


def add_emergency_term(
    Q: np.ndarray,
    offset: float,
    emergency_constraints: Optional[EmergencyConstraints],
) -> Tuple[np.ndarray, float]:
    """Add H_emergency linear contributions to matrix Q and update scalar offset.

    Formula:
        For each k in route:
            v = VARIABLE_INDEX[(k, forced_duration)]
            Q[v, v] += -F
            offset += F

    Args:
        Q: 2D numpy array of shape (NUM_VARIABLES, NUM_VARIABLES), upper-triangular.
        offset: Current scalar constant offset.
        emergency_constraints: Active emergency constraints or None.

    Returns:
        Tuple[np.ndarray, float]: Updated (Q, offset).
    """
    if Q.shape != (NUM_VARIABLES, NUM_VARIABLES):
        raise ValueError(
            f"Matrix Q must have shape ({NUM_VARIABLES}, {NUM_VARIABLES}), got {Q.shape}."
        )

    if emergency_constraints is None:
        return Q, offset

    F = emergency_constraints.emergency_weight
    forced_dur = emergency_constraints.forced_duration
    updated_offset = offset

    for k in emergency_constraints.route:
        v = get_variable_index(k, forced_dur)
        Q[v, v] += -F
        updated_offset += F

    return Q, updated_offset


def evaluate_emergency(
    x: Sequence[int],
    emergency_constraints: Optional[EmergencyConstraints],
) -> float:
    """Direct mathematical evaluation of the emergency constraint penalty H_emergency(x).

    Formula:
        H_emergency(x) = F * sum_{k in route} (1 - x_{k, forced_duration})

    Args:
        x: Binary state vector of length NUM_VARIABLES (12).
        emergency_constraints: Active EmergencyConstraints or None.

    Returns:
        float: Exact penalty value (0.0 if all route intersections have x_{k, forced_duration} = 1).
    """
    if emergency_constraints is None:
        return 0.0

    x_vec = np.asarray(x, dtype=np.float64)
    if len(x_vec) != NUM_VARIABLES:
        raise ValueError(
            f"State vector x must have length {NUM_VARIABLES}, got {len(x_vec)}."
        )

    F = emergency_constraints.emergency_weight
    forced_dur = emergency_constraints.forced_duration
    total_penalty = 0.0

    for k in emergency_constraints.route:
        v = get_variable_index(k, forced_dur)
        is_active = x_vec[v]
        total_penalty += F * (1.0 - is_active)

    return float(total_penalty)


def build_emergency_qubo(
    emergency_constraints: Optional[EmergencyConstraints],
) -> QUBOModel:
    """Build an isolated QUBOModel containing solely the emergency constraint terms.

    Args:
        emergency_constraints: Active emergency constraints.

    Returns:
        QUBOModel: Isolated upper-triangular QUBO model for H_emergency.
    """
    Q = np.zeros((NUM_VARIABLES, NUM_VARIABLES), dtype=np.float64)
    offset = 0.0
    Q, offset = add_emergency_term(Q, offset, emergency_constraints)

    canonical_var_order = tuple(
        INDEX_TO_VARIABLE[idx] for idx in range(NUM_VARIABLES)
    )

    metadata: Dict[str, Any] = {
        "term": "H_emergency",
        "has_emergency": emergency_constraints is not None,
        "route": list(emergency_constraints.route) if emergency_constraints else [],
        "forced_duration": emergency_constraints.forced_duration if emergency_constraints else None,
        "emergency_weight": emergency_constraints.emergency_weight if emergency_constraints else 0.0,
        "offset_contribution": offset,
    }

    return QUBOModel(
        Q=Q,
        variable_order=canonical_var_order,
        offset=offset,
        metadata=metadata,
    )
