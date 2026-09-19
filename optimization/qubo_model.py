"""Authoritative QUBO Model and Energy Evaluation.

Strictly follows the Upper Triangular QUBO Convention:
    E(x) = x^T Q x
where:
    - x is a binary column vector in {0, 1}^n
    - Q is an n x n upper-triangular matrix (Q[i, j] = 0 for i > j)
    - Linear terms: Q[i, i] * x_i (since x_i^2 = x_i)
    - Quadratic interaction terms: Q[i, j] * x_i * x_j for i < j
    - No double-counting: lower-triangular entries are strictly 0.0
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple, Any, Sequence, Union, Optional
import numpy as np

from optimization.variables import NUM_VARIABLES, INDEX_TO_VARIABLE


def qubo_energy(
    Q: Union[np.ndarray, Dict[Tuple[int, int], float]],
    x: Sequence[int],
) -> float:
    """Calculate the exact QUBO objective energy for a binary vector x.

    Mathematical Definition:
        E(x) = x^T Q x = sum_{i} Q[i, i] x_i + sum_{i < j} Q[i, j] x_i x_j

    This function serves as the single source of truth across all modules.

    Args:
        Q: Upper-triangular matrix (as a 2D numpy array) or dict of {(i, j): coeff}
           where i <= j.
        x: Binary state sequence of 0s and 1s.

    Returns:
        float: Exact evaluated energy E(x).

    Raises:
        ValueError: If x contains non-binary elements or if dimensions mismatch.
    """
    x_vec = np.asarray(x, dtype=np.float64)
    if not np.all(np.isin(x_vec, [0.0, 1.0])):
        raise ValueError(f"State vector x must contain only binary values in {{0, 1}}. Got: {x}")

    if isinstance(Q, dict):
        total_energy = 0.0
        n = len(x_vec)
        for (i, j), coeff in Q.items():
            if i > j:
                raise ValueError(
                    f"Invalid QUBO dictionary key ({i}, {j}). "
                    f"Only upper-triangular keys (i <= j) are permitted."
                )
            if i >= n or j >= n or i < 0 or j < 0:
                raise ValueError(
                    f"QUBO index ({i}, {j}) out of bounds for vector of length {n}."
                )
            total_energy += coeff * x_vec[i] * x_vec[j]
        return float(total_energy)

    elif isinstance(Q, np.ndarray):
        if Q.ndim != 2 or Q.shape[0] != Q.shape[1]:
            raise ValueError(f"Matrix Q must be 2D square. Got shape: {Q.shape}")
        if len(x_vec) != Q.shape[0]:
            raise ValueError(
                f"Dimension mismatch: Q is {Q.shape[0]}x{Q.shape[1]} but x has length {len(x_vec)}"
            )

        # Check for non-zero lower triangular entries to prevent accidental convention mismatch
        lower_tri = np.tril(Q, -1)
        if not np.allclose(lower_tri, 0.0):
            raise ValueError(
                "Matrix Q violates upper-triangular convention: lower-triangular entries must be 0.0."
            )

        # Standard matrix product: x^T Q x
        energy = float(x_vec @ Q @ x_vec)
        return energy
    else:
        raise TypeError(f"Unsupported type for Q: {type(Q)}. Expected np.ndarray or dict.")


@dataclass(frozen=True)
class QUBOModel:
    """Structured container representing an exact upper-triangular QUBO problem.

    Attributes:
        Q: 2D numpy array containing upper-triangular quadratic and linear coefficients.
        variable_order: Canonical tuple of (intersection_id, duration) pairs.
        offset: Constant energy offset derived from constraint expansions (e.g. sum(x_i - 1)^2).
        metadata: Detailed diagnostic breakdown (weights, active terms, term counts).
    """

    Q: np.ndarray
    variable_order: Tuple[Tuple[str, int], ...]
    offset: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate structural integrity of the QUBO model upon instantiation."""
        if not isinstance(self.Q, np.ndarray):
            object.__setattr__(self, "Q", np.asarray(self.Q, dtype=np.float64))

        if self.Q.ndim != 2 or self.Q.shape[0] != self.Q.shape[1]:
            raise ValueError(f"Q must be a square 2D array. Shape: {self.Q.shape}")

        num_vars = len(self.variable_order)
        if self.Q.shape[0] != num_vars:
            raise ValueError(
                f"Dimension mismatch: Q shape {self.Q.shape} does not match variable count {num_vars}"
            )

        # Enforce upper triangular constraint
        lower_tri = np.tril(self.Q, -1)
        if not np.allclose(lower_tri, 0.0):
            raise ValueError(
                "QUBOModel requires an upper-triangular Q matrix (all lower-triangular entries must be 0)."
            )

    @property
    def num_variables(self) -> int:
        """Return the number of binary decision variables."""
        return self.Q.shape[0]

    def energy(self, x: Sequence[int], include_offset: bool = True) -> float:
        """Evaluate the objective energy for candidate state x.

        Args:
            x: Binary vector in {0, 1}^n
            include_offset: If True, adds the constant offset.

        Returns:
            Total energy value.
        """
        raw_energy = qubo_energy(self.Q, x)
        return raw_energy + (self.offset if include_offset else 0.0)

    def to_dict(self) -> Dict[Tuple[int, int], float]:
        """Convert upper-triangular Q matrix to a sparse dictionary representation.

        Returns:
            Dictionary of {(i, j): coeff} for all non-zero entries where i <= j.
        """
        qubo_dict: Dict[Tuple[int, int], float] = {}
        rows, cols = np.nonzero(self.Q)
        for r, c in zip(rows, cols):
            if r <= c:
                val = float(self.Q[r, c])
                if not np.isclose(val, 0.0):
                    qubo_dict[(int(r), int(c))] = val
        return qubo_dict
