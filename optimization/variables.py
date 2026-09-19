"""Authoritative variable definitions and indexing for QuantumFlow QUBO.

Strictly defines the 12 binary decision variables representing the green phase
timing choices across the 4 intersections.
"""

from typing import Dict, Tuple, List

# Authoritative intersections and green duration choices
INTERSECTIONS: Tuple[str, ...] = ("I1", "I2", "I3", "I4")
DURATIONS: Tuple[int, ...] = (15, 30, 45)
NUM_VARIABLES: int = len(INTERSECTIONS) * len(DURATIONS)  # Exactly 12

# Canonical mapping from (intersection_id, duration_seconds) -> variable index (0..11)
VARIABLE_INDEX: Dict[Tuple[str, int], int] = {
    ("I1", 15): 0,
    ("I1", 30): 1,
    ("I1", 45): 2,
    ("I2", 15): 3,
    ("I2", 30): 4,
    ("I2", 45): 5,
    ("I3", 15): 6,
    ("I3", 30): 7,
    ("I3", 45): 8,
    ("I4", 15): 9,
    ("I4", 30): 10,
    ("I4", 45): 11,
}

# Reverse mapping from variable index -> (intersection_id, duration_seconds)
INDEX_TO_VARIABLE: Dict[int, Tuple[str, int]] = {
    idx: var for var, idx in VARIABLE_INDEX.items()
}

# String representation for each variable index
VARIABLE_NAMES: Tuple[str, ...] = tuple(
    f"{inter}_{dur}" for inter in INTERSECTIONS for dur in DURATIONS
)


def get_variable_index(intersection: str, duration: int) -> int:
    """Retrieve the unique index for a given intersection and duration choice.

    Args:
        intersection: Intersection identifier (e.g., 'I1')
        duration: Green time duration in seconds (15, 30, or 45)

    Returns:
        Zero-based integer index in range [0, 11]

    Raises:
        KeyError: If intersection or duration is not in the canonical set.
    """
    key = (intersection, duration)
    if key not in VARIABLE_INDEX:
        raise KeyError(
            f"Invalid decision variable {key}. Supported intersections: {INTERSECTIONS}, "
            f"supported durations: {DURATIONS}."
        )
    return VARIABLE_INDEX[key]


def get_intersection_variable_indices(intersection: str) -> List[int]:
    """Retrieve all variable indices associated with a specific intersection.

    Args:
        intersection: Intersection identifier (e.g. 'I1')

    Returns:
        List of 3 indices corresponding to durations 15, 30, 45
    """
    if intersection not in INTERSECTIONS:
        raise KeyError(f"Unknown intersection '{intersection}'. Expected one of {INTERSECTIONS}.")
    return [VARIABLE_INDEX[(intersection, dur)] for dur in DURATIONS]
