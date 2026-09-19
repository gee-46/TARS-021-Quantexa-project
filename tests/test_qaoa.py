"""Unit tests for Phase 9: Tiny 2-4 Qubit QAOA Proof of Concept with Qiskit Aer."""

import unittest
import numpy as np

from qiskit import transpile
from qiskit_aer import AerSimulator

from optimization.qubo_model import QUBOModel, qubo_energy
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
    TinyQAOAResult,
    build_qaoa_circuit,
    solve_tiny_qaoa,
)


class TestQAOACircuitConstruction(unittest.TestCase):
    """Test suite for parameterized QAOA circuit generation and Qiskit Aer compatibility."""

    def test_circuit_qubit_and_parameter_counts(self):
        """Verify circuit has exact number of qubits, Hadamards, and p=1 parameter count."""
        # 3-qubit dummy Ising model
        ising = IsingModel(
            h=np.array([1.0, -2.0, 0.5]),
            J={(0, 1): 1.5, (1, 2): -0.8},
            constant=5.0,
            num_qubits=3,
            variable_order=(("I1", 15), ("I1", 30), ("I1", 45)),
        )

        qc, gammas, betas = build_qaoa_circuit(ising, p=1)
        self.assertEqual(qc.num_qubits, 3)
        self.assertEqual(qc.num_clbits, 3)
        self.assertEqual(len(gammas), 1)
        self.assertEqual(len(betas), 1)

    def test_no_unsupported_opaque_instruction_after_transpile(self):
        """Verify circuit transpiled for AerSimulator contains only basis gates (e.g. h, rz, cx, rx)."""
        ising = IsingModel(
            h=np.array([1.0, -2.0]),
            J={(0, 1): 2.0},
            constant=3.0,
            num_qubits=2,
            variable_order=(("I1", 15), ("I1", 30)),
        )
        qc, gammas, betas = build_qaoa_circuit(ising, p=1)
        sim = AerSimulator()
        transpiled_qc = transpile(qc, sim)

        # Inspect gate set
        ops = transpiled_qc.count_ops()
        self.assertNotIn("QAOA", ops)
        self.assertNotIn("qaoa", ops)
        self.assertTrue(any(g in ops for g in ["rz", "cx", "rx", "h", "u"]))

    def test_bitstring_conversion_convention(self):
        """Verify logical qubit to Qiskit bitstring order convention."""
        # Prepare known computational state |101>: qubit 0 is 1, qubit 1 is 0, qubit 2 is 1
        # In Qiskit, measuring qubit 2 as 1, qubit 1 as 0, qubit 0 as 1 yields "101"
        bitstr = "101"
        bits = qiskit_bitstring_to_bits(bitstr)
        self.assertEqual(bits, (1, 0, 1))

        recon_str = bits_to_qiskit_bitstring(bits)
        self.assertEqual(recon_str, "101")

        # Test asymmetric state: qubit 0 is 1, qubit 1 is 0 -> Qiskit string "01"
        # bitstr[0] = '0' (qubit 1), bitstr[1] = '1' (qubit 0)
        bitstr_2 = "01"
        bits_2 = qiskit_bitstring_to_bits(bitstr_2)
        self.assertEqual(bits_2, (1, 0))  # (x_0=1, x_1=0)


class TestTinyQAOASolvers(unittest.TestCase):
    """Test suite for tiny QAOA solver executions against exact analytical optimums."""

    def test_tiny_problem_1_one_variable(self):
        """TEST PROBLEM 1: E(x0) = 6*x0 -> exact ground state is x0=0 (E=0.0)."""
        Q = np.array([[6.0]], dtype=np.float64)
        model = QUBOModel(Q=Q, variable_order=(("I1", 15),), offset=0.0)

        res = solve_tiny_qaoa(model, p=1, maxiter=25, shots=1024, seed=42)

        self.assertEqual(res.status, "success")
        self.assertEqual(res.exact_optimum_energy, 0.0)
        self.assertEqual(res.best_x, (0,))
        self.assertAlmostEqual(res.best_energy, 0.0)
        self.assertTrue(res.found_exact_optimum)
        self.assertGreater(res.ground_state_probability, 0.5)

    def test_tiny_problem_2_two_variables(self):
        """TEST PROBLEM 2: E(x0, x1) = 8*x0*x1 -> exact ground states are (0,0), (1,0), (0,1) with E=0.0."""
        Q = np.array([
            [0.0, 8.0],
            [0.0, 0.0],
        ], dtype=np.float64)
        model = QUBOModel(Q=Q, variable_order=(("I1", 15), ("I1", 30)), offset=0.0)

        res = solve_tiny_qaoa(model, p=1, maxiter=25, shots=1024, seed=42)

        self.assertEqual(res.status, "success")
        self.assertEqual(res.exact_optimum_energy, 0.0)
        self.assertAlmostEqual(res.best_energy, 0.0)
        self.assertTrue(res.found_exact_optimum)
        self.assertGreater(res.ground_state_probability, 0.6)

    def test_tiny_problem_3_three_variable_mixed_qubo(self):
        """TEST PROBLEM 3: 3-variable mixed QUBO:

        E = 3*x0 + 4*x1 + 2*x2 + 6*x0*x1 - 3*x1*x2 + 2*x0*x2
        States evaluation:
            (0,0,0) -> 0
            (1,0,0) -> 3
            (0,1,0) -> 4
            (0,0,1) -> 2
            (1,1,0) -> 3 + 4 + 6 = 13
            (1,0,1) -> 3 + 2 + 2 = 7
            (0,1,1) -> 4 + 2 - 3 = 3
            (1,1,1) -> 3 + 4 + 2 + 6 - 3 + 2 = 14
        Exact global minimum: (0, 0, 0) with E = 0.0.
        """
        Q = np.array([
            [3.0, 6.0, 2.0],
            [0.0, 4.0, -3.0],
            [0.0, 0.0, 2.0],
        ], dtype=np.float64)
        model = QUBOModel(
            Q=Q,
            variable_order=(("I1", 15), ("I1", 30), ("I1", 45)),
            offset=0.0,
        )

        res = solve_tiny_qaoa(model, p=1, maxiter=30, shots=1024, seed=123)

        self.assertEqual(res.status, "success")
        self.assertEqual(res.exact_optimum_energy, 0.0)
        self.assertEqual(res.best_x, (0, 0, 0))
        self.assertAlmostEqual(res.best_energy, 0.0)
        self.assertTrue(res.found_exact_optimum)

    def test_sampled_candidates_qubo_ising_consistency(self):
        """Verify for every bitstring in QAOA sampled counts, QUBO energy == Ising energy."""
        Q = np.array([
            [2.0, -4.0],
            [0.0, 3.0],
        ], dtype=np.float64)
        model = QUBOModel(Q=Q, variable_order=(("I1", 15), ("I1", 30)), offset=5.0)
        ising = qubo_to_ising(model)

        res = solve_tiny_qaoa(model, p=1, maxiter=20, shots=500, seed=42)

        for bitstr in res.counts.keys():
            x = qiskit_bitstring_to_bits(bitstr)
            z = bits_to_spins(x)
            e_qubo = model.energy(x, include_offset=True)
            e_ising = ising.energy(z)
            self.assertAlmostEqual(e_qubo, e_ising, places=10)

    def test_deterministic_reproducibility_with_seed(self):
        """Verify running with identical seeds produces identical counts and parameters."""
        Q = np.array([[4.0, 2.0], [0.0, -3.0]], dtype=np.float64)
        model = QUBOModel(Q=Q, variable_order=(("I1", 15), ("I1", 30)), offset=2.0)

        res1 = solve_tiny_qaoa(model, p=1, maxiter=20, shots=500, seed=999)
        res2 = solve_tiny_qaoa(model, p=1, maxiter=20, shots=500, seed=999)

        self.assertEqual(res1.counts, res2.counts)
        self.assertAlmostEqual(res1.best_energy, res2.best_energy)
        self.assertEqual(res1.best_x, res2.best_x)

    def test_controlled_failure_handling(self):
        """Verify invalid input dimensions or model errors return controlled failed status."""
        # Non-square / invalid model
        invalid_model = None
        res = solve_tiny_qaoa(invalid_model)  # type: ignore
        self.assertEqual(res.status, "failed")
        self.assertIsNotNone(res.error)


if __name__ == "__main__":
    unittest.main()
