"""Unit tests for Phase 12: Hybrid QAOA + Classical Fallback Orchestrator."""

import unittest
from unittest.mock import patch, MagicMock
import numpy as np

from optimization.variables import (
    NUM_VARIABLES,
    INDEX_TO_VARIABLE,
    VARIABLE_NAMES,
)
from optimization.qubo_model import QUBOModel, qubo_energy
from optimization.traffic_objectives import TrafficState
from optimization.emergency import EmergencyConstraints
from optimization.qubo_builder import FullQUBOConfig, build_qubo
from optimization.production_qaoa import ProductionQAOAResult
from optimization.sa_solver import SimulatedAnnealingResult
from optimization.hybrid_solver import HybridSolveResult, solve_hybrid


class TestHybridSolver(unittest.TestCase):
    """Test suite for Hybrid Optimization Orchestrator with mock and live executions."""

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

        # Valid candidate: 001001001001 -> I1_45, I2_45, I3_45, I4_45
        self.valid_x = (0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1)
        self.valid_bitstr = "001001001001"
        self.valid_energy = float(self.qubo_model.energy(self.valid_x, include_offset=True))

    def _make_mock_qaoa_result(
        self,
        status="success",
        best_x=None,
        best_bitstr=None,
        best_energy=None,
        timed_out=False,
        error=None,
    ) -> ProductionQAOAResult:
        x = best_x if best_x is not None else self.valid_x
        bs = best_bitstr if best_bitstr is not None else self.valid_bitstr
        e = best_energy if best_energy is not None else self.valid_energy
        return ProductionQAOAResult(
            status=status,
            error=error,
            p=1,
            num_qubits=12,
            maxiter=30,
            optimization_iterations=25,
            shots=1024,
            optimized_parameters=[0.1, 0.1],
            expectation_value=350.0,
            counts={"100100100100": 1024},
            best_bitstring="100100100100",
            best_canonical_bitstring=bs,
            best_x=x,
            best_z=tuple(1 - 2 * b for b in x) if x else (),
            best_energy=e,
            qubo_energy=e,
            ising_energy=e,
            onehot_valid=True,
            emergency_valid=True,
            signal_plan={"I1": 45, "I2": 45, "I3": 45, "I4": 45} if x else None,
            runtime_seconds=1.2,
            timed_out=timed_out,
            ground_state_probability=1.0,
        )

    def _make_mock_sa_result(
        self,
        status="success",
        best_x=None,
        best_bitstr=None,
        best_energy=None,
        error=None,
    ) -> SimulatedAnnealingResult:
        x = best_x if best_x is not None else self.valid_x
        bs = best_bitstr if best_bitstr is not None else self.valid_bitstr
        e = best_energy if best_energy is not None else self.valid_energy
        return SimulatedAnnealingResult(
            status=status,
            error=error,
            num_reads=100,
            num_sweeps=1000,
            seed=42,
            num_variables=12,
            best_bitstring=bs,
            best_x=x,
            best_energy=e,
            qubo_energy=e,
            bqm_energy=e,
            runtime_seconds=0.015,
            samples_considered=100,
            sample_distribution={bs: 100},
            onehot_valid=True,
            emergency_valid=True,
            signal_plan={"I1": 45, "I2": 45, "I3": 45, "I4": 45} if x else None,
        )

    # TEST 1 & 12: QAOA valid -> no fallback, SA not called
    @patch("optimization.hybrid_solver.solve_simulated_annealing")
    @patch("optimization.hybrid_solver.solve_production_qaoa")
    def test_qaoa_valid_no_fallback(self, mock_qaoa, mock_sa):
        """When QAOA candidate is valid, return QAOA result and do NOT call SA."""
        mock_qaoa.return_value = self._make_mock_qaoa_result()

        result = solve_hybrid(
            qubo_model=self.qubo_model,
            emergency_constraints=self.emergency,
        )

        mock_qaoa.assert_called_once()
        mock_sa.assert_not_called()
        self.assertEqual(result.status, "success")
        self.assertEqual(result.solver_used, "qaoa")
        self.assertFalse(result.fallback_used)
        self.assertIsNone(result.fallback_reason)
        self.assertIsNotNone(result.qaoa_result)
        self.assertIsNone(result.sa_result)
        self.assertEqual(result.best_x, self.valid_x)
        self.assertAlmostEqual(result.best_energy, self.valid_energy)

    # TEST 2 & 10: QAOA timeout -> SA fallback
    @patch("optimization.hybrid_solver.solve_simulated_annealing")
    @patch("optimization.hybrid_solver.solve_production_qaoa")
    def test_qaoa_timeout_triggers_sa_fallback(self, mock_qaoa, mock_sa):
        """When QAOA times out, fallback to SA with reason 'qaoa_timeout'."""
        mock_qaoa.return_value = self._make_mock_qaoa_result(status="timeout", timed_out=True)
        mock_sa.return_value = self._make_mock_sa_result()

        result = solve_hybrid(
            qubo_model=self.qubo_model,
            emergency_constraints=self.emergency,
        )

        mock_qaoa.assert_called_once()
        mock_sa.assert_called_once()
        self.assertEqual(result.status, "success")
        self.assertEqual(result.solver_used, "sa")
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.fallback_reason, "qaoa_timeout")
        self.assertIsNotNone(result.qaoa_result)
        self.assertIsNotNone(result.sa_result)

    # TEST 3 & 10: QAOA failed -> SA fallback
    @patch("optimization.hybrid_solver.solve_simulated_annealing")
    @patch("optimization.hybrid_solver.solve_production_qaoa")
    def test_qaoa_failed_triggers_sa_fallback(self, mock_qaoa, mock_sa):
        """When QAOA fails, fallback to SA with reason 'qaoa_failed'."""
        mock_qaoa.return_value = self._make_mock_qaoa_result(
            status="failed",
            best_x=(),
            best_bitstr="",
            best_energy=float("inf"),
            error="Simulation error",
        )
        mock_sa.return_value = self._make_mock_sa_result()

        result = solve_hybrid(
            qubo_model=self.qubo_model,
            emergency_constraints=self.emergency,
        )

        mock_qaoa.assert_called_once()
        mock_sa.assert_called_once()
        self.assertEqual(result.status, "success")
        self.assertEqual(result.solver_used, "sa")
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.fallback_reason, "qaoa_failed")

    # TEST 4 & 10: Invalid one-hot -> SA fallback
    @patch("optimization.hybrid_solver.solve_simulated_annealing")
    @patch("optimization.hybrid_solver.solve_production_qaoa")
    def test_invalid_onehot_triggers_sa_fallback(self, mock_qaoa, mock_sa):
        """When QAOA returns non-one-hot state, trigger SA fallback with 'invalid_onehot'."""
        # Invalid state: I1 has two active bits (1, 1, 0)
        invalid_x = (1, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1)
        mock_qaoa.return_value = self._make_mock_qaoa_result(
            best_x=invalid_x,
            best_bitstr="110001001001",
        )
        mock_sa.return_value = self._make_mock_sa_result()

        result = solve_hybrid(
            qubo_model=self.qubo_model,
            require_onehot=True,
            emergency_constraints=self.emergency,
        )

        mock_sa.assert_called_once()
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.fallback_reason, "invalid_onehot")
        self.assertEqual(result.solver_used, "sa")

    # TEST 5 & 10: Invalid emergency corridor -> SA fallback
    @patch("optimization.hybrid_solver.solve_simulated_annealing")
    @patch("optimization.hybrid_solver.solve_production_qaoa")
    def test_invalid_emergency_triggers_sa_fallback(self, mock_qaoa, mock_sa):
        """When QAOA violates emergency constraints, trigger SA fallback with 'invalid_emergency'."""
        # I2 has duration 15 (index 3) instead of forced 45 (index 5)
        invalid_emerg_x = (0, 0, 1, 1, 0, 0, 0, 0, 1, 0, 0, 1)
        mock_qaoa.return_value = self._make_mock_qaoa_result(
            best_x=invalid_emerg_x,
            best_bitstr="001100001001",
        )
        mock_sa.return_value = self._make_mock_sa_result()

        result = solve_hybrid(
            qubo_model=self.qubo_model,
            require_emergency_valid=True,
            emergency_constraints=self.emergency,
        )

        mock_sa.assert_called_once()
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.fallback_reason, "invalid_emergency")
        self.assertEqual(result.solver_used, "sa")

    # TEST 6 & 10: Invalid/non-finite candidate energy -> SA fallback
    @patch("optimization.hybrid_solver.solve_simulated_annealing")
    @patch("optimization.hybrid_solver.solve_production_qaoa")
    def test_invalid_candidate_triggers_sa_fallback(self, mock_qaoa, mock_sa):
        """When QAOA returns invalid candidate length or non-binary elements, trigger SA fallback."""
        mock_qaoa.return_value = self._make_mock_qaoa_result(best_x=(1, 0, 2))  # invalid length & values
        mock_sa.return_value = self._make_mock_sa_result()

        result = solve_hybrid(qubo_model=self.qubo_model)

        mock_sa.assert_called_once()
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.fallback_reason, "invalid_candidate")
        self.assertEqual(result.solver_used, "sa")

    # TEST 7: Final QAOA energy matches original QUBO
    @patch("optimization.hybrid_solver.solve_production_qaoa")
    def test_final_qaoa_energy_matches_original_qubo(self, mock_qaoa):
        """Verify accepted QAOA solution energy is evaluated directly against original QUBO."""
        mock_qaoa.return_value = self._make_mock_qaoa_result()

        result = solve_hybrid(qubo_model=self.qubo_model, emergency_constraints=self.emergency)

        expected_e = float(self.qubo_model.energy(result.best_x, include_offset=True))
        self.assertAlmostEqual(result.best_energy, expected_e, places=10)
        self.assertAlmostEqual(result.qubo_energy, expected_e, places=10)

    # TEST 8: Final SA energy matches original QUBO
    @patch("optimization.hybrid_solver.solve_simulated_annealing")
    @patch("optimization.hybrid_solver.solve_production_qaoa")
    def test_final_sa_energy_matches_original_qubo(self, mock_qaoa, mock_sa):
        """Verify accepted SA fallback solution energy is evaluated directly against original QUBO."""
        mock_qaoa.return_value = self._make_mock_qaoa_result(status="timeout", timed_out=True)
        mock_sa.return_value = self._make_mock_sa_result()

        result = solve_hybrid(qubo_model=self.qubo_model, emergency_constraints=self.emergency)

        expected_e = float(self.qubo_model.energy(result.best_x, include_offset=True))
        self.assertAlmostEqual(result.best_energy, expected_e, places=10)
        self.assertAlmostEqual(result.qubo_energy, expected_e, places=10)

    # TEST 9 & 11: Deterministic Phase 7 Scenario (Live integration test)
    def test_live_deterministic_phase7_scenario(self):
        """Execute unmocked hybrid solve on Phase 7 scenario; verify QAOA succeeds and no fallback occurs."""
        result = solve_hybrid(
            qubo_model=self.qubo_model,
            qaoa_p=1,
            qaoa_maxiter=30,
            qaoa_shots=1024,
            qaoa_seed=42,
            qaoa_timeout_seconds=60.0,
            require_onehot=True,
            require_emergency_valid=True,
            emergency_constraints=self.emergency,
        )

        self.assertEqual(result.status, "success")
        self.assertEqual(result.solver_used, "qaoa")
        self.assertFalse(result.fallback_used)
        self.assertIsNone(result.fallback_reason)
        self.assertIsNotNone(result.qaoa_result)
        self.assertIsNone(result.sa_result)
        self.assertTrue(result.onehot_valid)
        self.assertTrue(result.emergency_valid)
        self.assertIsNotNone(result.signal_plan)
        expected_e = float(self.qubo_model.energy(result.best_x, include_offset=True))
        self.assertAlmostEqual(result.best_energy, expected_e, places=8)

    # TEST: Both QAOA and SA fail handling
    @patch("optimization.hybrid_solver.solve_simulated_annealing")
    @patch("optimization.hybrid_solver.solve_production_qaoa")
    def test_both_solvers_fail(self, mock_qaoa, mock_sa):
        """When QAOA fails and SA fallback also fails, return status='failed' with diagnostics."""
        mock_qaoa.return_value = self._make_mock_qaoa_result(status="failed", error="QAOA crash")
        mock_sa.return_value = self._make_mock_sa_result(status="failed", best_x=(), error="SA crash")

        result = solve_hybrid(qubo_model=self.qubo_model)

        self.assertEqual(result.status, "failed")
        self.assertEqual(result.solver_used, "sa")
        self.assertTrue(result.fallback_used)
        self.assertEqual(result.fallback_reason, "qaoa_failed")
        self.assertIsNotNone(result.error)


if __name__ == "__main__":
    unittest.main()
