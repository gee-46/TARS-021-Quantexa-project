"""Authoritative QUBO to Ising Hamiltonian Transformation and Verification.

Converts upper-triangular QUBO formulations E_QUBO(x) = x^T Q x + offset into exact Ising Hamiltonians:
    H_Ising(z) = constant + sum_i h_i z_i + sum_{i < j} J_ij z_i z_j

Using the canonical binary-to-spin mapping:
    x_i = (1 - z_i) / 2,   where x_i in {0, 1} and z_i in {-1, +1} (eigenvalues of Pauli Z_i)
    x_i = 0  -->  z_i = +1
    x_i = 1  -->  z_i = -1

Transformation Derivation:
1. Linear/Diagonal Terms:
   Q_ii * x_i = Q_ii * (1 - z_i) / 2 = Q_ii / 2 - (Q_ii / 2) * z_i
   --> constant += Q_ii / 2,   h_i += -Q_ii / 2

2. Quadratic/Off-Diagonal Terms (for i < j):
   Q_ij * x_i * x_j = Q_ij * ((1 - z_i)(1 - z_j)) / 4
                    = Q_ij / 4 - (Q_ij / 4) * z_i - (Q_ij / 4) * z_j + (Q_ij / 4) * z_i * z_j
   --> constant += Q_ij / 4,   h_i += -Q_ij / 4,   h_j += -Q_ij / 4,   J_ij += Q_ij / 4

3. Total Constant Offset:
   constant = offset + sum_i (Q_ii / 2) + sum_{i < j} (Q_ij / 4)
"""

from dataclasses import dataclass, field
from typing import Sequence, Tuple, Dict, Any, Union, Optional
import numpy as np

from optimization.qubo_model import QUBOModel, qubo_energy


def bits_to_spins(x: Sequence[int]) -> np.ndarray:
    """Convert binary vector x in {0, 1}^n to spin vector z in {-1, +1}^n.

    Formula:
        z_i = 1 - 2 * x_i
        x_i = 0 -> z_i = +1
        x_i = 1 -> z_i = -1
    """
    x_vec = np.asarray(x, dtype=np.float64)
    if not np.all(np.isin(x_vec, [0.0, 1.0])):
        raise ValueError(f"Input bits must be strictly in {{0, 1}}, got: {x}")
    return 1.0 - 2.0 * x_vec


def spins_to_bits(z: Sequence[int]) -> np.ndarray:
    """Convert spin vector z in {-1, +1}^n to binary vector x in {0, 1}^n.

    Formula:
        x_i = (1 - z_i) / 2
        z_i = +1 -> x_i = 0
        z_i = -1 -> x_i = 1
    """
    z_vec = np.asarray(z, dtype=np.float64)
    if not np.all(np.isin(z_vec, [-1.0, 1.0])):
        raise ValueError(f"Input spins must be strictly in {{-1, +1}}, got: {z}")
    return ((1.0 - z_vec) / 2.0).astype(np.int64)


@dataclass(frozen=True)
class IsingModel:
    """Immutable representation of an exact Ising spin Hamiltonian.

    Attributes:
        h: 1D numpy array of linear magnetic field coefficients h_i for Pauli Z_i.
        J: Dictionary of {(i, j): coeff} for quadratic spin couplings Z_i Z_j (i < j).
        constant: Constant energy baseline including QUBO offset and algebraic shifts.
        num_qubits: Total number of spin/qubit sites n.
        variable_order: Canonical variable mapping tuples.
        metadata: Diagnostic provenance metadata from the source QUBOModel.
    """

    h: np.ndarray
    J: Dict[Tuple[int, int], float]
    constant: float
    num_qubits: int
    variable_order: Tuple[Tuple[str, int], ...]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate structural consistency of the Ising model."""
        if not isinstance(self.h, np.ndarray):
            object.__setattr__(self, "h", np.asarray(self.h, dtype=np.float64))

        if self.h.ndim != 1 or len(self.h) != self.num_qubits:
            raise ValueError(
                f"Ising vector h must have shape ({self.num_qubits},), got {self.h.shape}."
            )

        for (i, j) in self.J.keys():
            if not (0 <= i < j < self.num_qubits):
                raise ValueError(
                    f"Invalid Ising coupling pair ({i}, {j}). Must satisfy 0 <= i < j < {self.num_qubits}."
                )

    def energy(self, spins: Sequence[int]) -> float:
        """Evaluate the exact Ising energy for a spin configuration z in {-1, +1}^n.

        Formula:
            E(z) = constant + sum_i h_i z_i + sum_{i < j} J_ij z_i z_j
        """
        return ising_energy(spins, self)


def ising_energy(spins: Sequence[int], ising_model: IsingModel) -> float:
    """Evaluate exact energy of an Ising Hamiltonian for a spin vector z.

    Args:
        spins: Spin state sequence in {-1, +1}^n.
        ising_model: Target IsingModel.

    Returns:
        float: Exact evaluated energy E(z).
    """
    z_vec = np.asarray(spins, dtype=np.float64)
    if len(z_vec) != ising_model.num_qubits:
        raise ValueError(
            f"Spin vector length {len(z_vec)} does not match Ising site count {ising_model.num_qubits}."
        )
    if not np.all(np.isin(z_vec, [-1.0, 1.0])):
        raise ValueError(f"Spin values must be strictly in {{-1, +1}}, got: {spins}")

    # Constant term
    total = ising_model.constant

    # Linear terms: sum_i h_i z_i
    total += float(np.dot(ising_model.h, z_vec))

    # Quadratic interaction terms: sum_{i < j} J_ij z_i z_j
    for (i, j), coeff in ising_model.J.items():
        total += coeff * z_vec[i] * z_vec[j]

    return float(total)


def qubo_to_ising(qubo_model: QUBOModel) -> IsingModel:
    """Convert an upper-triangular QUBOModel into an exact IsingModel.

    Mathematical Translation:
        constant = offset + sum_i Q[i, i] / 2 + sum_{i < j} Q[i, j] / 4
        h_i = -Q[i, i] / 2 - sum_{j < i} Q[j, i] / 4 - sum_{j > i} Q[i, j] / 4
        J_ij = Q[i, j] / 4   (for i < j)

    Args:
        qubo_model: Input QUBOModel with upper-triangular matrix Q and scalar offset.

    Returns:
        IsingModel: Exact mathematically equivalent Ising Hamiltonian representation.
    """
    Q = qubo_model.Q
    n = qubo_model.num_variables
    offset = qubo_model.offset

    h = np.zeros(n, dtype=np.float64)
    J: Dict[Tuple[int, int], float] = {}
    constant = float(offset)

    # 1. Process diagonal terms: Q[i, i] * x_i
    for i in range(n):
        q_ii = float(Q[i, i])
        if not np.isclose(q_ii, 0.0):
            constant += q_ii / 2.0
            h[i] += -q_ii / 2.0

    # 2. Process off-diagonal interaction terms: Q[i, j] * x_i * x_j (for i < j)
    for i in range(n):
        for j in range(i + 1, n):
            q_ij = float(Q[i, j])
            if not np.isclose(q_ij, 0.0):
                constant += q_ij / 4.0
                h[i] += -q_ij / 4.0
                h[j] += -q_ij / 4.0
                J[(i, j)] = q_ij / 4.0

    metadata: Dict[str, Any] = {
        "source": "qubo_to_ising",
        "qubo_offset": offset,
        "ising_constant": constant,
        "num_linear_terms": int(np.count_nonzero(~np.isclose(h, 0.0))),
        "num_quadratic_couplings": len(J),
        "source_metadata": qubo_model.metadata,
    }

    return IsingModel(
        h=h,
        J=J,
        constant=constant,
        num_qubits=n,
        variable_order=qubo_model.variable_order,
        metadata=metadata,
    )


def ising_to_qiskit_operator(ising_model: IsingModel):
    """Optional bridge: Convert IsingModel to a Qiskit SparsePauliOp and energy offset.

    Returns:
        Tuple[SparsePauliOp, float]: (cost_operator, constant_offset)
    """
    from qiskit.quantum_info import SparsePauliOp

    pauli_list = []
    n = ising_model.num_qubits

    # Linear terms: h_i * Z_i
    # Note on Qiskit Pauli string indexing: char at string index 0 is qubit (n-1), char at (n-1) is qubit 0.
    for i in range(n):
        coeff = float(ising_model.h[i])
        if not np.isclose(coeff, 0.0):
            chars = ["I"] * n
            chars[n - 1 - i] = "Z"
            pauli_list.append(("".join(chars), coeff))

    # Quadratic terms: J_ij * Z_i Z_j
    for (i, j), coeff in ising_model.J.items():
        if not np.isclose(coeff, 0.0):
            chars = ["I"] * n
            chars[n - 1 - i] = "Z"
            chars[n - 1 - j] = "Z"
            pauli_list.append(("".join(chars), coeff))

    if not pauli_list:
        # Trivial all-identity operator
        op = SparsePauliOp.from_list([("I" * n, 0.0)])
    else:
        op = SparsePauliOp.from_list(pauli_list)

    return op, ising_model.constant
