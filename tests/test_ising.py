"""Unit tests for exact QUBO to Ising Hamiltonian Transformation and Equivalence."""

import unittest
import itertools
import numpy as np

from optimization.variables import (
    INTERSECTIONS,
    DURATIONS,
    NUM_VARIABLES,
    VARIABLE_INDEX,
    INDEX_TO_VARIABLE,
)
from optimization.qubo_model import QUBOModel, qubo_energy
from optimization.traffic_objectives import TrafficState
from optimization.emergency import EmergencyConstraints
from optimization.qubo_builder import FullQUBOConfig, build_qubo
from optimization.enumeration import enumerate_qubo_states
from optimization.ising_converter import (
    bits_to_spins,
    spins_to_bits,
    IsingModel,
    ising_energy,
    qubo_to_ising,
    ising_to_qiskit_operator,
)


class TestBitSpinConversions(unittest.TestCase):
    """Test suite for binary-to-spin and spin-to-binary mapping helpers."""

    def test_bit_to_spin_mapping(self):
        """Verify x=0 -> z=+1 and x=1 -> z=-1."""
        bits = [0, 1, 0, 1]
        expected_spins = [1.0, -1.0, 1.0, -1.0]
        spins = bits_to_spins(bits)
        self.assertTrue(np.allclose(spins, expected_spins))

    def test_spin_to_bit_mapping(self):
        """Verify z=+1 -> x=0 and z=-1 -> x=1."""
        spins = [1.0, -1.0, 1.0, -1.0]
        expected_bits = [0, 1, 0, 1]
        bits = spins_to_bits(spins)
        self.assertTrue(np.allclose(bits, expected_bits))

    def test_round_trip_conversion(self):
        """Verify spins_to_bits(bits_to_spins(x)) == x for all 2^4 = 16 states."""
        for bits in itertools.product([0, 1], repeat=4):
            x = list(bits)
            z = bits_to_spins(x)
            x_recon = spins_to_bits(z).tolist()
            self.assertEqual(x, x_recon)

    def test_invalid_bit_or_spin_values(self):
        """Verify validation errors for non-binary bits or non-spin values."""
        with self.assertRaises(ValueError):
            bits_to_spins([0, 2, 1])
        with self.assertRaises(ValueError):
            spins_to_bits([1.0, 0.0, -1.0])


class TestAnalyticalIsingMappings(unittest.TestCase):
    """Test suite for analytical term-by-term QUBO to Ising derivations."""

    def test_case_a_single_linear_term(self):
        """TEST A: E = 6*x0.

        Using x0 = (1 - z0)/2:
            6*x0 = 3 - 3*z0
            constant = 3, h0 = -3
        """
        Q = np.array([[6.0]], dtype=np.float64)
        model = QUBOModel(Q=Q, variable_order=(("I1", 15),), offset=0.0)
        ising = qubo_to_ising(model)

        self.assertAlmostEqual(ising.constant, 3.0)
        self.assertAlmostEqual(ising.h[0], -3.0)
        self.assertEqual(len(ising.J), 0)

        # Check energies for both states
        # x=0 -> z=+1 -> E = 0
        self.assertAlmostEqual(ising.energy([1]), 0.0)
        self.assertAlmostEqual(model.energy([0]), 0.0)

        # x=1 -> z=-1 -> E = 6
        self.assertAlmostEqual(ising.energy([-1]), 6.0)
        self.assertAlmostEqual(model.energy([1]), 6.0)

    def test_case_b_single_quadratic_term(self):
        """TEST B: E = 8*x0*x1.

        Using x0 = (1 - z0)/2, x1 = (1 - z1)/2:
            8*x0*x1 = 2 - 2*z0 - 2*z1 + 2*z0*z1
            constant = 2, h0 = -2, h1 = -2, J01 = +2
        """
        Q = np.array([
            [0.0, 8.0],
            [0.0, 0.0],
        ], dtype=np.float64)
        model = QUBOModel(Q=Q, variable_order=(("I1", 15), ("I1", 30)), offset=0.0)
        ising = qubo_to_ising(model)

        self.assertAlmostEqual(ising.constant, 2.0)
        self.assertAlmostEqual(ising.h[0], -2.0)
        self.assertAlmostEqual(ising.h[1], -2.0)
        self.assertAlmostEqual(ising.J[(0, 1)], 2.0)

        # Verify all 4 states
        # (0, 0) -> (+1, +1) -> E = 0
        self.assertAlmostEqual(ising.energy([1, 1]), 0.0)
        # (1, 0) -> (-1, +1) -> E = 0
        self.assertAlmostEqual(ising.energy([-1, 1]), 0.0)
        # (0, 1) -> (+1, -1) -> E = 0
        self.assertAlmostEqual(ising.energy([1, -1]), 0.0)
        # (1, 1) -> (-1, -1) -> E = 8
        self.assertAlmostEqual(ising.energy([-1, -1]), 8.0)

    def test_case_c_constant_offset(self):
        """TEST C: E = 5 + 6*x0 -> constant = 5 + 3 = 8, h0 = -3."""
        Q = np.array([[6.0]], dtype=np.float64)
        model = QUBOModel(Q=Q, variable_order=(("I1", 15),), offset=5.0)
        ising = qubo_to_ising(model)

        self.assertAlmostEqual(ising.constant, 8.0)
        self.assertAlmostEqual(ising.h[0], -3.0)

        # x=0 (z=+1) -> E = 5
        self.assertAlmostEqual(ising.energy([1]), 5.0)
        # x=1 (z=-1) -> E = 11
        self.assertAlmostEqual(ising.energy([-1]), 11.0)

    def test_case_d_mixed_3var_qubo(self):
        """TEST D: E = 10 + 4*x0 - 6*x1 + 2*x2 + 8*x0*x1 - 4*x0*x2 + 12*x1*x2.

        Derivation:
            offset = 10
            Diagonals:
                4*x0 -> const +2, h0 -2
               -6*x1 -> const -3, h1 +3
                2*x2 -> const +1, h2 -1
            Off-diagonals:
                8*x0*x1 -> const +2, h0 -2, h1 -2, J01 +2
               -4*x0*x2 -> const -1, h0 +1, h2 +1, J02 -1
               12*x1*x2 -> const +3, h1 -3, h2 -3, J12 +3

            Total Constant = 10 + 2 - 3 + 1 + 2 - 1 + 3 = 14.0
            Total h0 = -2 - 2 + 1 = -3.0
            Total h1 = +3 - 2 - 3 = -2.0
            Total h2 = -1 + 1 - 3 = -3.0
            J01 = +2.0
            J02 = -1.0
            J12 = +3.0
        """
        Q = np.array([
            [4.0, 8.0, -4.0],
            [0.0, -6.0, 12.0],
            [0.0, 0.0, 2.0],
        ], dtype=np.float64)
        model = QUBOModel(
            Q=Q,
            variable_order=(("I1", 15), ("I1", 30), ("I1", 45)),
            offset=10.0,
        )
        ising = qubo_to_ising(model)

        self.assertAlmostEqual(ising.constant, 14.0)
        self.assertAlmostEqual(ising.h[0], -3.0)
        self.assertAlmostEqual(ising.h[1], -2.0)
        self.assertAlmostEqual(ising.h[2], -3.0)
        self.assertAlmostEqual(ising.J[(0, 1)], 2.0)
        self.assertAlmostEqual(ising.J[(0, 2)], -1.0)
        self.assertAlmostEqual(ising.J[(1, 2)], 3.0)

        # Exhaustively check all 2^3 = 8 states
        for bits in itertools.product([0, 1], repeat=3):
            x = list(bits)
            z = bits_to_spins(x)
            e_qubo = model.energy(x, include_offset=True)
            e_ising = ising.energy(z)
            self.assertAlmostEqual(e_qubo, e_ising)


class TestFullTrafficQUBOToIsing(unittest.TestCase):
    """Test suite for Exact Equivalence on the complete 12-variable traffic network."""

    def setUp(self):
        self.state_dict = {
            "I1": {"queue": 20.0, "density": 0.50, "capacity": 100.0},
            "I2": {"queue": 35.0, "density": 0.90, "capacity": 100.0},
            "I3": {"queue": 15.0, "density": 0.60, "capacity": 100.0},
            "I4": {"queue": 30.0, "density": 0.80, "capacity": 100.0},
        }
        self.traffic_state = TrafficState.from_dict(self.state_dict)
        self.edges = [("I1", "I2"), ("I2", "I3"), ("I3", "I4")]
        self.emergency = EmergencyConstraints(route=["I2", "I3", "I4"], forced_duration=45, emergency_weight=50.0)
        self.config = FullQUBOConfig()

        self.qubo_model = build_qubo(
            traffic_state=self.traffic_state,
            edges=self.edges,
            config=self.config,
            emergency_constraints=self.emergency,
        )
        self.ising_model = qubo_to_ising(self.qubo_model)

    def test_exact_energy_equivalence_all_4096_states(self):
        """CRITICAL TEST: Verify E_QUBO(x) == E_Ising(z) for ALL 4096 binary states."""
        max_abs_diff = 0.0

        for bits in itertools.product([0, 1], repeat=NUM_VARIABLES):
            x = list(bits)
            z = bits_to_spins(x)

            e_qubo = self.qubo_model.energy(x, include_offset=True)
            e_ising = self.ising_model.energy(z)

            diff = abs(e_qubo - e_ising)
            if diff > max_abs_diff:
                max_abs_diff = diff

            self.assertAlmostEqual(
                e_qubo,
                e_ising,
                places=10,
                msg=f"Discrepancy at bitstring {''.join(str(b) for b in bits)}: QUBO={e_qubo}, Ising={e_ising}",
            )

        self.assertLess(max_abs_diff, 1e-10)

    def test_ground_state_and_optimum_consistency(self):
        """Verify ground state spin configuration corresponds to Phase 7 global optimum bitstring."""
        analysis = enumerate_qubo_states(
            qubo_model=self.qubo_model,
            traffic_state=self.traffic_state,
            edges=self.edges,
            config=self.config,
            emergency_constraints=self.emergency,
        )
        opt_x = list(analysis.best_unconstrained.state)
        opt_energy = analysis.best_unconstrained.energy

        opt_z = bits_to_spins(opt_x)
        ising_opt_energy = self.ising_model.energy(opt_z)

        self.assertAlmostEqual(opt_energy, ising_opt_energy, places=10)

    def test_qiskit_sparse_pauli_op_bridge(self):
        """Verify optional Qiskit SparsePauliOp builder produces matching expectation values."""
        op, const = ising_to_qiskit_operator(self.ising_model)
        self.assertEqual(op.num_qubits, 12)
        self.assertAlmostEqual(const, self.ising_model.constant)


class TestRandomizedIsingEquivalence(unittest.TestCase):
    """Test suite for randomized QUBO matrices with mixed signs and arbitrary offsets."""

    def test_random_matrices_exact_equivalence(self):
        """Verify multiple randomized upper-triangular QUBOs across random binary vectors."""
        rng = np.random.default_rng(seed=2026)

        for trial in range(10):
            n = int(rng.integers(2, 9))
            Q_dense = rng.uniform(-20.0, 20.0, size=(n, n))
            Q_upper = np.triu(Q_dense)
            offset = float(rng.uniform(-100.0, 100.0))

            var_order = tuple((f"V{i}", 1) for i in range(n))
            qubo = QUBOModel(Q=Q_upper, variable_order=var_order, offset=offset)
            ising = qubo_to_ising(qubo)

            # Test 50 random states per matrix
            for _ in range(50):
                x = rng.choice([0, 1], size=n).tolist()
                z = bits_to_spins(x)
                e_q = qubo.energy(x, include_offset=True)
                e_i = ising.energy(z)
                self.assertAlmostEqual(e_q, e_i, places=10)


if __name__ == "__main__":
    unittest.main()
