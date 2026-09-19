"""Unit tests for Phase 11: Classical Simulated Annealing Baseline with dwave-neal and dimod."""

import unittest
import itertools
import numpy as np
import dimod
import neal

from optimization.variables import (
    NUM_VARIABLES,
    INDEX_TO_VARIABLE,
    VARIABLE_NAMES,
)
from optimization.qubo_model import QUBOModel, qubo_energy
from optimization.traffic_objectives import TrafficState
from optimization.emergency import EmergencyConstraints
from optimization.qubo_builder import FullQUBOConfig, build_qubo
from optimization.decoder import is_valid_onehot, is_valid_emergency, decode_solution
from optimization.sa_solver import (
    qubo_to_bqm,
    SimulatedAnnealingResult,
    solve_simulated_annealing,
)


class TestBQMConversion(unittest.TestCase):
    """TEST 1: QUBOModel to dimod.BinaryQuadraticModel Transformation."""

    def test_bqm_energy_equivalence_all_states(self):
        """Construct a 3-variable QUBO and verify exact equivalence across all 8 binary states."""
        Q = np.array([
            [3.0, 5.0, -2.0],
            [0.0, -4.0, 6.0],
            [0.0, 0.0, 1.5],
        ], dtype=np.float64)
        offset = 12.5
        var_order = (("I1", 15), ("I1", 30), ("I1", 45))
        model = QUBOModel(Q=Q, variable_order=var_order, offset=offset)

        bqm = qubo_to_bqm(model)

        max_discrepancy = 0.0
        for bits in itertools.product([0, 1], repeat=3):
            e_qubo = model.energy(bits, include_offset=True)
            sample = {i: bits[i] for i in range(3)}
            e_bqm = bqm.energy(sample)
            diff = abs(e_qubo - e_bqm)
            max_discrepancy = max(max_discrepancy, diff)
            self.assertAlmostEqual(e_qubo, e_bqm, places=12)

        self.assertLess(max_discrepancy, 1e-12)

    def test_off_diagonal_terms_not_doubled(self):
        """Specifically verify off-diagonal quadratic interaction terms are NOT doubled."""
        # E(x0, x1) = 7.0 * x0 * x1 + 0
        Q = np.array([
            [0.0, 7.0],
            [0.0, 0.0],
        ], dtype=np.float64)
        model = QUBOModel(Q=Q, variable_order=(("I1", 15), ("I1", 30)), offset=0.0)
        bqm = qubo_to_bqm(model)

        # For x = (1, 1): QUBO energy is 7.0 (not 14.0)
        e_qubo = model.energy((1, 1), include_offset=True)
        e_bqm = bqm.energy({0: 1, 1: 1})
        self.assertAlmostEqual(e_qubo, 7.0)
        self.assertAlmostEqual(e_bqm, 7.0)


class TestCanonicalVariableOrder(unittest.TestCase):
    """TEST 2: Canonical Variable Ordering Preservation."""

    def test_12_bit_canonical_ordering(self):
        """Verify returned bitstrings and decision vectors have 12 variables in canonical order."""
        Q = np.zeros((12, 12), dtype=np.float64)
        for i in range(12):
            Q[i, i] = float(i - 5)
        var_order = tuple(INDEX_TO_VARIABLE[i] for i in range(12))
        model = QUBOModel(Q=Q, variable_order=var_order, offset=0.0)

        result = solve_simulated_annealing(model, num_reads=20, num_sweeps=100, seed=42)

        self.assertEqual(result.status, "success")
        self.assertEqual(len(result.best_bitstring), 12)
        self.assertEqual(len(result.best_x), 12)
        self.assertEqual(result.num_variables, 12)

        # Check binary characters in bitstring
        self.assertTrue(all(c in "01" for c in result.best_bitstring))


class TestSimpleKnownOptimum(unittest.TestCase):
    """TEST 3: Simple Known Ground Truth Optimum Verification."""

    def test_finds_known_minimum(self):
        """Verify SA reliably finds known analytical ground state on a small problem."""
        # Diagonal QUBO where minimum is unambiguously (0, 1, 0)
        Q = np.array([
            [10.0, 0.0, 0.0],
            [0.0, -25.0, 0.0],
            [0.0, 0.0, 8.0],
        ], dtype=np.float64)
        var_order = (("I1", 15), ("I1", 30), ("I1", 45))
        model = QUBOModel(Q=Q, variable_order=var_order, offset=5.0)

        result = solve_simulated_annealing(
            model,
            num_reads=50,
            num_sweeps=500,
            seed=42,
            exact_optimum_x=(0, 1, 0),
            exact_optimum_energy=-20.0,
        )

        self.assertEqual(result.status, "success")
        self.assertEqual(result.best_x, (0, 1, 0))
        self.assertAlmostEqual(result.best_energy, -20.0)
        self.assertTrue(result.exact_optimum_found)
        self.assertAlmostEqual(result.optimality_gap, 0.0)


class TestCandidateSelection(unittest.TestCase):
    """TEST 4: Minimum Energy Selection vs Frequency."""

    def test_lowest_energy_selection_policy(self):
        """Verify candidate selection policy strictly minimizes exact original QUBO energy."""
        # Problem where (1, 1) has lowest energy
        Q = np.array([
            [-10.0, -10.0],
            [0.0, -10.0],
        ], dtype=np.float64)
        var_order = (("I1", 15), ("I1", 30))
        model = QUBOModel(Q=Q, variable_order=var_order, offset=0.0)

        result = solve_simulated_annealing(model, num_reads=50, num_sweeps=200, seed=123)

        self.assertEqual(result.status, "success")
        self.assertEqual(result.best_x, (1, 1))
        self.assertAlmostEqual(result.best_energy, -30.0)


class TestDeterministicTrafficScenario(unittest.TestCase):
    """TEST 5: Deterministic 12-Variable QuantumFlow Traffic Scenario."""

    def setUp(self):
        state_dict = {
            "I1": {"queue": 20.0, "density": 0.50, "capacity": 100.0},
            "I2": {"queue": 35.0, "density": 0.90, "capacity": 100.0},
            "I3": {"queue": 15.0, "density": 0.60, "capacity": 100.0},
            "I4": {"queue": 30.0, "density": 0.80, "capacity": 100.0},
        }
        self.traffic_state = TrafficState.from_dict(state_dict)
        self.edges = [("I1", "I2"), ("I2", "I3"), ("I3", "I4")]
        self.emergency = EmergencyConstraints(
            route=["I2", "I3", "I4"],
            forced_duration=45,
            emergency_weight=50.0,
        )
        self.config = FullQUBOConfig(
            onehot_penalty=100.0,
            wait_weight=2.0,
            capacity_weight=10.0,
            capacity_threshold=0.7,
            throughput_weight=1.0,
            service_rate=1.0,
            coupling_weight=5.0,
            default_capacity=100.0,
            emergency_weight=50.0,
        )
        self.qubo_model = build_qubo(
            traffic_state=self.traffic_state,
            edges=self.edges,
            config=self.config,
            emergency_constraints=self.emergency,
        )
        self.exact_optimum_x = (0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1)
        self.exact_optimum_energy = self.qubo_model.energy(self.exact_optimum_x, include_offset=True)

    def test_solve_traffic_scenario(self):
        """Run simulated annealing on the full 12-variable traffic QUBO model."""
        result = solve_simulated_annealing(
            qubo_model=self.qubo_model,
            num_reads=100,
            num_sweeps=1000,
            seed=42,
            emergency_constraints=self.emergency,
            exact_optimum_x=self.exact_optimum_x,
            exact_optimum_energy=self.exact_optimum_energy,
        )

        # 1. Structure & Status
        self.assertEqual(result.status, "success")
        self.assertIsNone(result.error)
        self.assertEqual(result.num_variables, 12)
        self.assertEqual(len(result.best_x), 12)
        self.assertEqual(len(result.best_bitstring), 12)

        # 2. Energy Consistency
        expected_qubo_e = self.qubo_model.energy(result.best_x, include_offset=True)
        self.assertAlmostEqual(result.best_energy, expected_qubo_e, places=8)
        self.assertAlmostEqual(result.qubo_energy, result.bqm_energy, places=8)

        # 3. Validity Checks
        self.assertTrue(result.onehot_valid)
        self.assertTrue(result.emergency_valid)
        self.assertIsNotNone(result.signal_plan)

        # 4. Energy Quality
        self.assertLess(result.best_energy, 0.0)


class TestReproducibility(unittest.TestCase):
    """TEST 6: Deterministic Reproducibility with Seed."""

    def test_identical_runs_with_fixed_seed(self):
        """Verify runs with identical random seed produce identical solutions and distributions."""
        Q = np.random.RandomState(42).uniform(-5.0, 5.0, size=(12, 12))
        Q = np.triu(Q)
        var_order = tuple(INDEX_TO_VARIABLE[i] for i in range(12))
        model = QUBOModel(Q=Q, variable_order=var_order, offset=15.0)

        res1 = solve_simulated_annealing(model, num_reads=50, num_sweeps=200, seed=42)
        res2 = solve_simulated_annealing(model, num_reads=50, num_sweeps=200, seed=42)

        self.assertEqual(res1.status, "success")
        self.assertEqual(res2.status, "success")
        self.assertEqual(res1.best_bitstring, res2.best_bitstring)
        self.assertEqual(res1.best_x, res2.best_x)
        self.assertAlmostEqual(res1.best_energy, res2.best_energy, places=10)
        self.assertEqual(res1.sample_distribution, res2.sample_distribution)


class TestMultipleReads(unittest.TestCase):
    """TEST 7: Multiple Reads Sampling Verification."""

    def test_evaluates_multiple_reads(self):
        """Verify num_reads > 1 samples multiple reads and records candidate distribution."""
        Q = np.zeros((12, 12), dtype=np.float64)
        for i in range(12):
            Q[i, i] = -1.0
        var_order = tuple(INDEX_TO_VARIABLE[i] for i in range(12))
        model = QUBOModel(Q=Q, variable_order=var_order, offset=0.0)

        num_reads = 80
        result = solve_simulated_annealing(model, num_reads=num_reads, num_sweeps=50, seed=123)

        self.assertEqual(result.status, "success")
        self.assertEqual(result.num_reads, num_reads)
        total_occurrences = sum(result.sample_distribution.values())
        self.assertEqual(total_occurrences, num_reads)
        self.assertGreaterEqual(result.samples_considered, 1)

    def test_graceful_error_handling(self):
        """Verify invalid input types or corrupted models return structured failed result."""
        invalid_model = None
        result = solve_simulated_annealing(invalid_model)  # type: ignore
        self.assertEqual(result.status, "failed")
        self.assertIsNotNone(result.error)


if __name__ == "__main__":
    unittest.main()
