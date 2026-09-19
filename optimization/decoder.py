"""Authoritative Solution Decoder and Validator.

Converts 12-bit binary decision vectors into structured intersection signal timing plans:
    x in {0, 1}^12  -->  {"I1": 15/30/45, "I2": 15/30/45, "I3": 15/30/45, "I4": 15/30/45}

Validation Rules:
- Length must be exactly NUM_VARIABLES (12).
- Values must be strictly binary {0, 1}.
- One-Hot: Exactly one duration active per intersection (total active bits = 4).
- Emergency: All corridor route intersections must have x_{k, forced_duration} = 1.
- No Silent Repair: Invalid solutions raise explicit validation exceptions.
"""

from typing import Dict, Sequence, Tuple, Optional, Any, Union
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
from optimization.emergency import EmergencyConstraints


def is_valid_onehot(x: Sequence[int]) -> bool:
    """Check if binary state x satisfies the one-hot constraint across all intersections.

    Args:
        x: Binary state sequence.

    Returns:
        bool: True if and only if each of the 4 intersections has exactly 1 active duration.
    """
    x_vec = np.asarray(x, dtype=np.float64)
    if len(x_vec) != NUM_VARIABLES:
        return False
    if not np.all(np.isin(x_vec, [0.0, 1.0])):
        return False

    for inter in INTERSECTIONS:
        indices = get_intersection_variable_indices(inter)
        if np.sum(x_vec[indices]) != 1.0:
            return False

    return True


def is_valid_emergency(
    x: Sequence[int],
    emergency_constraints: Optional[Any],
) -> bool:
    """Check if binary state x satisfies active emergency corridor constraints.

    Args:
        x: Binary state sequence.
        emergency_constraints: Active EmergencyConstraints, route tuple, or dict.

    Returns:
        bool: True if emergency_constraints is None or if all route intersections
              have x_{k, forced_duration} == 1.
    """
    if emergency_constraints is None:
        return True

    x_vec = np.asarray(x, dtype=np.float64)
    if len(x_vec) != NUM_VARIABLES:
        return False

    if isinstance(emergency_constraints, dict):
        for k, forced_dur in emergency_constraints.items():
            v = get_variable_index(k, int(forced_dur))
            if x_vec[v] != 1.0:
                return False
        return True

    if isinstance(emergency_constraints, (tuple, list)):
        for k in emergency_constraints:
            v = get_variable_index(k, 45)
            if x_vec[v] != 1.0:
                return False
        return True

    forced_dur = getattr(emergency_constraints, "forced_duration", 45)
    route = getattr(emergency_constraints, "route", ())
    for k in route:
        v = get_variable_index(k, forced_dur)
        if x_vec[v] != 1.0:
            return False

    return True


def validate_solution(
    x: Sequence[int],
    emergency_constraints: Optional[EmergencyConstraints] = None,
) -> Tuple[bool, Optional[str]]:
    """Perform comprehensive structural and domain validation on candidate binary solution x.

    Args:
        x: Binary candidate sequence.
        emergency_constraints: Optional active emergency constraints.

    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    x_vec = np.asarray(x, dtype=np.float64)
    if len(x_vec) != NUM_VARIABLES:
        return False, f"Invalid length: expected {NUM_VARIABLES} bits, got {len(x_vec)}."

    if not np.all(np.isin(x_vec, [0.0, 1.0])):
        return False, "Non-binary values detected in solution vector."

    for inter in INTERSECTIONS:
        indices = get_intersection_variable_indices(inter)
        active_count = int(np.sum(x_vec[indices]))
        if active_count != 1:
            return False, f"Intersection '{inter}' violates one-hot constraint (active durations: {active_count})."

    if emergency_constraints is not None:
        forced_dur = emergency_constraints.forced_duration
        for k in emergency_constraints.route:
            v = get_variable_index(k, forced_dur)
            if x_vec[v] != 1.0:
                return (
                    False,
                    f"Emergency route intersection '{k}' failed to allocate forced duration {forced_dur}s.",
                )

    return True, None


def decode_solution(x: Sequence[int]) -> Dict[str, int]:
    """Decode a valid 12-bit binary decision vector into a signal timing plan.

    Args:
        x: Binary state sequence of length 12.

    Returns:
        Dict[str, int]: Signal timing plan, e.g. {"I1": 30, "I2": 45, "I3": 15, "I4": 30}.

    Raises:
        ValueError: If state x is malformed or violates one-hot constraints.
    """
    valid, err_msg = validate_solution(x, emergency_constraints=None)
    if not valid:
        raise ValueError(f"Cannot decode invalid signal solution: {err_msg}")

    x_vec = np.asarray(x, dtype=np.int64)
    signal_plan: Dict[str, int] = {}

    for inter in INTERSECTIONS:
        indices = get_intersection_variable_indices(inter)
        # Exactly one index is active
        active_idx = None
        for idx in indices:
            if x_vec[idx] == 1:
                active_idx = idx
                break
        if active_idx is None:
            raise ValueError(f"No active duration found for intersection '{inter}'.")

        _, duration = INDEX_TO_VARIABLE[active_idx]
        signal_plan[inter] = duration

    return signal_plan
