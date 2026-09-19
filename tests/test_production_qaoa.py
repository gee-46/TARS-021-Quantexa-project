"""Unit tests for Phase 10: Production 12-Qubit QAOA Solver for QuantumFlow."""

import unittest
import numpy as np

from qiskit import transpile
from qiskit_aer import AerSimulator

from optimization.variables import (
    NUM_VARIABLES,
    INDEX_TO_VARIABLE,
    VARIABLE_NAMES,
)
from optimization.qubo_model import QUBOModel, qubo_energy
from optimization.traffic_objectives import TrafficState
from optimization.emergency import EmergencyConstraints
from optimization.qubo_builder import FullQUBOConfig, build_qubo
from optimization.ising_converter import (
    IsingModel,
    bits_to_spins,
    spins_to_bits,
    ising_energy,
    qubo_to_ising,
)
from optimization.qaoa_solver import (
    qiskit_bitstring_to_bits,
    bits_to_qiskit_bitstring,
    build_qaoa_circuit,
)
from optimization.production_qaoa import (
    ProductionQAOAResult,
    solve_production_qaoa,
)


class TestProductionQAOACircuit(unittest.TestCase):
    """TEST 1: 12-Qubit QAOA Circuit Construction and Aer Transpilation."""

    def setUp(self):
        # Create a standard 12-variable QUBO model
        self.traffic_state = TrafficState.from_dict({
            "I1": {"queue": 20.0, "density": 0.50, "capacity": 100.0},
            "I2": {"queue": 35.0, "density": 0.90, "capacity": 100.0},
            "I3": {"queue": 15.0, "density": 0.60, "capacity": 100.0},
            "I4": {"queue": 30.0, "density": 0.80, "capacity": 100.0},
        })
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
        self.ising_model = qubo_to_ising(self.qubo_model)

    def test_12_qubit_circuit_structure(self):
        """Confirm exactly 12 qubits, 12 classical bits, and valid parameter counts."""
        qc, gammas, betas = build_qaoa_circuit(self.ising_model, p=1)
        self.assertEqual(qc.num_qubits, 12)
        self.assertEqual(qc.num_clbits, 12)
        self.assertEqual(len(gammas), 1)
        self.assertEqual(len(betas), 1)

    def test_aer_transpilation_and_supported_gates(self):
        """Confirm circuit has no opaque unsupported QAOA instructions and transpiles onto Aer."""
        qc, gammas, betas = build_qaoa_circuit(self.ising_model, p=1)
        sim = AerSimulator()
        transpiled_qc = transpile(qc, sim)

        ops = transpiled_qc.count_ops()
        self.assertNotIn("QAOA", ops)
        self.assertNotIn("qaoa", ops)
        self.assertTrue(any(g in ops for g in ["rz", "cx", "rx", "h", "u"]))

    def test_p2_circuit_structure(self):
        """Confirm p=2 QAOA circuit builds with 2 gamma and 2 beta parameters."""
        qc, gammas, betas = build_qaoa_circuit(self.ising_model, p=2)
        self.assertEqual(qc.num_qubits, 12)
        self.assertEqual(qc.num_clbits, 12)
        self.assertEqual(len(gammas), 2)
        self.assertEqual(len(betas), 2)


class TestIsingConsistency(unittest.TestCase):
    """TEST 2: Exact Ising and QUBO Energy Consistency across sampled candidates."""

    def test_sampled_candidates_ising_consistency(self):
        """Verify E_QUBO(x) == E_Ising(1 - 2x) for all sampled states."""
        # 12-variable diagonal QUBO with offsets
        np.random.seed(42)
        Q = np.zeros((12, 12), dtype=np.float64)
        for i in range(12):
            Q[i, i] = (i + 1) * 2.5
        for i in range(12):
            for j in range(i + 1, min(i + 3, 12)):
                Q[i, j] = 1.5 * (i + j)

        var_order = tuple(INDEX_TO_VARIABLE[i] for i in range(12))
        model = QUBOModel(Q=Q, variable_order=var_order, offset=42.0)
        ising = qubo_to_ising(model)

        result = solve_production_qaoa(
            qubo_model=model,
            p=1,
            maxiter=10,
            shots=256,
            seed=42,
            timeout_seconds=30.0,
        )

        self.assertEqual(result.status, "success")
        self.assertGreater(len(result.counts), 0)

        for bitstr in result.counts.keys():
            x = qiskit_bitstring_to_bits(bitstr)
            z = tuple(int(zi) for zi in bits_to_spins(x))
            e_qubo = model.energy(x, include_offset=True)
            e_ising = ising.energy(z)
            self.assertAlmostEqual(e_qubo, e_ising, places=10)


class TestDeterministicScenario(unittest.TestCase):
    """TEST 3: Full Deterministic 12-Variable Traffic Scenario Execution."""

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
        # Global minimum target from Phase 7 exhaustive enumeration:
        # bitstring 001001001001 -> I1_45, I2_45, I3_45, I4_45 with energy ~ -95.5556
        self.exact_optimum_x = (0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1)
        self.exact_optimum_energy = self.qubo_model.energy(self.exact_optimum_x, include_offset=True)

    def test_deterministic_qaoa_solve(self):
        """Execute production QAOA on deterministic scenario and verify structured result."""
        result = solve_production_qaoa(
            qubo_model=self.qubo_model,
            p=1,
            maxiter=30,
            shots=1024,
            seed=42,
            timeout_seconds=60.0,
            emergency_constraints=self.emergency,
            exact_optimum_x=self.exact_optimum_x,
        )

        # 1. Status & Structure
        self.assertEqual(result.status, "success")
        self.assertFalse(result.timed_out)
        self.assertIsNone(result.error)
        self.assertEqual(result.num_qubits, 12)
        self.assertEqual(result.p, 1)
        self.assertEqual(len(result.best_x), 12)
        self.assertEqual(len(result.best_z), 12)
        self.assertEqual(len(result.best_canonical_bitstring), 12)

        # 2. Energy Verification
        expected_qubo_e = self.qubo_model.energy(result.best_x, include_offset=True)
        self.assertAlmostEqual(result.best_energy, expected_qubo_e, places=8)
        self.assertAlmostEqual(result.qubo_energy, result.ising_energy, places=8)

        # 3. Best Sampled Candidate Energy should be reasonably low
        self.assertLess(result.best_energy, 200.0)


class TestCandidateSelection(unittest.TestCase):
    """TEST 4: Minimum Energy Selection vs Most Frequent Bitstring."""

    def test_selects_lowest_energy_not_highest_frequency(self):
        """Verify solver chooses lowest-energy candidate even if another state had higher frequency."""
        # Construct a simple 2-variable problem where (1, 1) has lowest energy
        # but the distribution may have higher count on (0, 0)
        Q = np.array([
            [-5.0, -10.0],
            [0.0, -5.0],
        ], dtype=np.float64)
        var_order = (("I1", 15), ("I1", 30))
        model = QUBOModel(Q=Q, variable_order=var_order, offset=0.0)

        # Solve QAOA
        result = solve_production_qaoa(
            qubo_model=model,
            p=1,
            maxiter=15,
            shots=512,
            seed=42,
        )

        self.assertEqual(result.status, "success")
        # Ensure best_energy is indeed the minimum across all observed states in counts
        sampled_energies = [
            model.energy(qiskit_bitstring_to_bits(bs), include_offset=True)
            for bs in result.counts.keys()
        ]
        self.assertAlmostEqual(result.best_energy, min(sampled_energies), places=10)
        self.assertEqual(result.best_x, (1, 1))


class TestBitOrdering(unittest.TestCase):
    """TEST 5: Canonical 12-Bit Order Mapping from Qiskit Endianness."""

    def test_12_bit_ordering_conversion(self):
        """Verify 12-bit computational basis state conversion to and from canonical x."""
        # Let state have 1 at variable index 0 (I1_15) and index 11 (I4_45)
        canonical_x = (1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1)
        # In Qiskit bitstring:
        # bitstr[0] = x_11 = 1, bitstr[1..10] = 0, bitstr[11] = x_0 = 1
        qiskit_str = bits_to_qiskit_bitstring(canonical_x)
        self.assertEqual(qiskit_str, "100000000001")

        recovered_x = qiskit_bitstring_to_bits(qiskit_str)
        self.assertEqual(recovered_x, canonical_x)

        # Canonical bitstring representation (x_0...x_11)
        canonical_str = "".join(str(b) for b in canonical_x)
        self.assertEqual(canonical_str, "100000000001")

        # Test asymmetric state: only x_2 (I1_45) = 1
        x_single = (0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        # Qiskit string: bitstr[12 - 1 - 2] = bitstr[9] = '1'
        q_single = bits_to_qiskit_bitstring(x_single)
        self.assertEqual(q_single, "000000000100")
        self.assertEqual(qiskit_bitstring_to_bits(q_single), x_single)


class TestTimeoutProtection(unittest.TestCase):
    """TEST 6: Timeout Protection and Graceful Early Termination."""

    def test_timeout_triggered_gracefully(self):
        """Verify solver terminates with status='timeout' when timeout_seconds is exceeded."""
        Q = np.zeros((12, 12), dtype=np.float64)
        for i in range(12):
            Q[i, i] = float(i)
        var_order = tuple(INDEX_TO_VARIABLE[i] for i in range(12))
        model = QUBOModel(Q=Q, variable_order=var_order, offset=0.0)

        # Set an extremely small timeout threshold
        result = solve_production_qaoa(
            qubo_model=model,
            p=1,
            maxiter=100,
            shots=1024,
            seed=42,
            timeout_seconds=0.000001,
        )

        self.assertEqual(result.status, "timeout")
        self.assertTrue(result.timed_out)
        self.assertIsNotNone(result.error)
        self.assertEqual(result.num_qubits, 12)
        self.assertGreaterEqual(result.runtime_seconds, 0.0)


class TestReproducibility(unittest.TestCase):
    """TEST 7: Deterministic Reproducibility with Fixed Seed."""

    def test_reproducibility_with_identical_seed(self):
        """Verify identical optimization trajectories and sampling with fixed seed."""
        Q = np.zeros((12, 12), dtype=np.float64)
        for i in range(12):
            Q[i, i] = -2.0 * (i + 1)
            if i < 11:
                Q[i, i + 1] = 1.0

        var_order = tuple(INDEX_TO_VARIABLE[i] for i in range(12))
        model = QUBOModel(Q=Q, variable_order=var_order, offset=10.0)

        res1 = solve_production_qaoa(
            qubo_model=model,
            p=1,
            maxiter=10,
            shots=256,
            seed=42,
            timeout_seconds=30.0,
        )
        res2 = solve_production_qaoa(
            qubo_model=model,
            p=1,
            maxiter=10,
            shots=256,
            seed=42,
            timeout_seconds=30.0,
        )

        self.assertEqual(res1.status, "success")
        self.assertEqual(res2.status, "success")
        self.assertEqual(res1.best_x, res2.best_x)
        self.assertAlmostEqual(res1.best_energy, res2.best_energy, places=10)
        self.assertEqual(res1.counts, res2.counts)
        self.assertEqual(res1.optimized_parameters, res2.optimized_parameters)


if __name__ == "__main__":
    unittest.main()
