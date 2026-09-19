# QUBO to Ising Hamiltonian Transformation Specification

## 1. Overview & Problem Definition

In **QuantumFlow**, multi-intersection traffic signal optimization is mathematically modeled as an unconstrained quadratic binary optimization (QUBO) problem over $n = 12$ binary decision variables $x \in \{0, 1\}^{12}$.

To execute the Quantum Approximate Optimization Algorithm (QAOA) using quantum circuit simulators, this QUBO formulation must be transformed into an equivalent **Ising Spin Hamiltonian** $H_{\text{Ising}}$ whose ground state maps directly to the global minimum of the traffic objective.

---

## 2. QUBO Convention

The authoritative QUBO convention utilized across QuantumFlow is:

$$E_{\text{QUBO}}(x) = x^T Q x + \text{offset} = \sum_{i=0}^{n-1} Q_{ii} x_i + \sum_{0 \le i < j < n} Q_{ij} x_i x_j + \text{offset}$$

where:
* $x \in \{0, 1\}^n$ is a binary column vector.
* $Q \in \mathbb{R}^{n \times n}$ is an **upper-triangular matrix** ($Q_{ji} = 0$ for $j > i$).
* $Q_{ii}$ stores the net linear coefficient for variable $x_i$ (since $x_i^2 = x_i$ for $x_i \in \{0, 1\}$).
* $Q_{ij}$ (for $i < j$) stores the exact pairwise interaction coefficient for $x_i x_j$.
* $\text{offset} \in \mathbb{R}$ tracks scalar constant energy contributions arising from one-hot constraints ($4A$) and active emergency corridor penalties ($F \cdot |\text{route}|$).

---

## 3. Canonical Binary-to-Spin Mapping

We map binary variables $x_i \in \{0, 1\}$ to spin variables $z_i \in \{-1, +1\}$ (the eigenvalues of the Pauli-$Z$ operator $\sigma^z$) via:

$$x_i = \frac{1 - z_i}{2}$$

**State Correspondence:**
* $x_i = 0 \iff z_i = +1 \iff |0\rangle$
* $x_i = 1 \iff z_i = -1 \iff |1\rangle$

**Inverse Mapping:**
$$z_i = 1 - 2x_i$$

---

## 4. Algebraic Transformation Derivation

### 4.1 Linear / Diagonal Terms ($Q_{ii} x_i$)
Substituting $x_i = \frac{1 - z_i}{2}$:

$$Q_{ii} x_i = Q_{ii} \left( \frac{1 - z_i}{2} \right) = \frac{Q_{ii}}{2} - \frac{Q_{ii}}{2} z_i$$

**Contributions to Ising Hamiltonian:**
* Energy constant shift: $+\frac{Q_{ii}}{2}$
* Linear magnetic field on site $i$: $-\frac{Q_{ii}}{2} z_i$

### 4.2 Quadratic / Off-Diagonal Terms ($Q_{ij} x_i x_j$ for $i < j$)
Substituting $x_i = \frac{1 - z_i}{2}$ and $x_j = \frac{1 - z_j}{2}$:

$$Q_{ij} x_i x_j = Q_{ij} \left( \frac{1 - z_i}{2} \right) \left( \frac{1 - z_j}{2} \right) = Q_{ij} \left( \frac{1 - z_i - z_j + z_i z_j}{4} \right) = \frac{Q_{ij}}{4} - \frac{Q_{ij}}{4} z_i - \frac{Q_{ij}}{4} z_j + \frac{Q_{ij}}{4} z_i z_j$$

**Contributions to Ising Hamiltonian:**
* Energy constant shift: $+\frac{Q_{ij}}{4}$
* Linear magnetic field on site $i$: $-\frac{Q_{ij}}{4} z_i$
* Linear magnetic field on site $j$: $-\frac{Q_{ij}}{4} z_j$
* Quadratic spin coupling between sites $i$ and $j$: $+\frac{Q_{ij}}{4} z_i z_j$

---

## 5. Master Ising Hamiltonian Formulation

The total Ising Hamiltonian is written as:

$$H_{\text{Ising}}(z) = C + \sum_{i=0}^{n-1} h_i z_i + \sum_{0 \le i < j < n} J_{ij} z_i z_j$$

where:

### 5.1 Constant Offset $C$:
$$C = \text{offset} + \sum_{i=0}^{n-1} \frac{Q_{ii}}{2} + \sum_{0 \le i < j < n} \frac{Q_{ij}}{4}$$

### 5.2 Local Fields $h_i$:
$$h_i = -\frac{Q_{ii}}{2} - \sum_{j < i} \frac{Q_{ji}}{4} - \sum_{j > i} \frac{Q_{ij}}{4}$$

### 5.3 Spin Couplings $J_{ij}$ (for $i < j$):
$$J_{ij} = \frac{Q_{ij}}{4}$$

---

## 6. Sign Properties & Physical Intuition

1. **Diagonal Penalties ($Q_{ii} > 0$)**: Incur $h_i < 0$, creating an energetic preference for $z_i = +1$ ($x_i = 0$).
2. **Diagonal Rewards ($Q_{ii} < 0$)**: Incur $h_i > 0$, creating an energetic preference for $z_i = -1$ ($x_i = 1$).
3. **Repulsive / Penalty Couplings ($Q_{ij} > 0$)**: Yield $J_{ij} > 0$ (ferromagnetic/anti-ferromagnetic alignment penalizing simultaneously active bits $x_i = x_j = 1 \implies z_i = z_j = -1$).

---

## 7. Exact Equivalence Theorem

**Theorem:** For any binary configuration $x \in \{0, 1\}^n$ and its corresponding spin configuration $z = 1 - 2x \in \{-1, +1\}^n$:

$$E_{\text{QUBO}}(x) \equiv H_{\text{Ising}}(z)$$

This identity is exact with zero algebraic truncation and is verified across all $2^{12} = 4096$ states of the full multi-intersection network in the test suite (`tests/test_ising.py`).

---

## 8. Qiskit Operator Mapping

In Qiskit, the cost Hamiltonian operator $H_C$ is constructed using `SparsePauliOp` from `qiskit.quantum_info`:

$$H_C = \sum_{i=0}^{n-1} h_i Z_i + \sum_{0 \le i < j < n} J_{ij} Z_i Z_j$$

* Note: The scalar constant $C$ produces a global phase shift during unitary evolution $e^{-i \gamma H_C}$ and does not affect the optimization landscape ($\text{argmin}_{\gamma, \beta} \langle \psi(\gamma, \beta) | H_C | \psi(\gamma, \beta) \rangle$), but is tracked explicitly for absolute energy reporting.
